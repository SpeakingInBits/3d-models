"""A background worker that builds models with some of their parameters changed.

The CAD libraries take about five seconds to load, so the app keeps this process running and sends
it one job per line on stdin, as JSON with the model's script and an output folder. The changes are
read from parameters.json in that folder. They replace the constants as the script is loaded, so
anything worked out from those constants follows them, and the script itself is left alone.

The worker prints READY once it has loaded, and ends each job with FINISHED and its exit code. It
stops when stdin closes, so it can't outlive the app.
"""

import ast
import json
import os
import sys
import traceback
from pathlib import Path

import bd_warehouse.thread  # noqa: F401  loaded here so that jobs don't wait for it
import build123d  # noqa: F401
import pyvista as pv

ROOT = Path(__file__).resolve().parent.parent
MM_PER_INCH = 25.4
READY = "@@ready"
FINISHED = "@@finished"


def apply_changes(tree, changes, out_dir):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            break
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name):
            if target.id == "OUT":
                node.value = ast.parse(f"Path({str(out_dir)!r})", mode="eval").body
            elif target.id in changes:
                node.value = ast.Constant(changes[target.id])
        elif isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
            for i, name in enumerate(target.elts):
                if name.id in changes:
                    node.value.elts[i] = ast.Constant(changes[name.id])
    ast.fix_missing_locations(tree)


def run_script(script, changes, out_dir):
    tree = ast.parse(script.read_text(encoding="utf-8"))
    apply_changes(tree, changes, out_dir)
    sys.path.insert(0, str(script.parent))
    sys.argv = [str(script)]
    exec(compile(tree, str(script), "exec"), {"__name__": "__main__", "__file__": str(script)})


def report(out_dir):
    """Print the size of each part in both units and render the biggest one."""
    meshes = [pv.read(stl) for stl in sorted(out_dir.glob("*.stl"))]
    print("\nfinished parts:")
    for stl, mesh in zip(sorted(out_dir.glob("*.stl")), meshes):
        x0, x1, y0, y1, z0, z1 = mesh.bounds
        size = (x1 - x0, y1 - y0, z1 - z0)
        print(f"  {stl.name}: {' x '.join(f'{v:.1f}' for v in size)} mm "
              f"({' x '.join(f'{v / MM_PER_INCH:.2f}' for v in size)} in)")

    p = pv.Plotter(off_screen=True, window_size=(1000, 700))
    p.set_background("#b9b9bd")
    p.add_mesh(max(meshes, key=lambda mesh: mesh.volume), color="#ece4d6", smooth_shading=True,
               split_sharp_edges=True, feature_angle=25, specular=0.25)
    p.remove_all_lights()
    p.add_light(pv.Light(light_type="headlight", intensity=0.85))
    p.view_vector((1, -1.6, 0.9), viewup=(0, 0, 1))
    p.screenshot(out_dir / "preview.png")
    p.close()


def forget_models():
    """Drop imported model scripts, because one model can change another's constants."""
    for name, module in list(sys.modules.items()):
        file = getattr(module, "__file__", None)
        if file and os.path.dirname(os.path.dirname(file)) == str(ROOT):
            del sys.modules[name]


def run_job(job):
    script, out_dir = Path(job["script"]), Path(job["folder"])
    search_path = list(sys.path)
    try:
        changes = json.loads((out_dir / "parameters.json").read_text(encoding="utf-8"))
        run_script(script, changes, out_dir)
        report(out_dir)
        return 0
    except (Exception, SystemExit):
        traceback.print_exc(file=sys.stdout)
        return 1
    finally:
        sys.path[:] = search_path
        forget_models()


def warm_up():
    """Do a throwaway render, because the first one in a process takes about a second longer."""
    p = pv.Plotter(off_screen=True, window_size=(100, 100))
    p.add_mesh(pv.Sphere(), smooth_shading=True, split_sharp_edges=True)
    p.screenshot()
    p.close()


def main():
    warm_up()
    print(READY, flush=True)
    for line in sys.stdin:
        print(f"{FINISHED} {run_job(json.loads(line))}", flush=True)


if __name__ == "__main__":
    main()
