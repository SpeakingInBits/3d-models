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
import numpy as np
from PIL import Image, ImageDraw

from models import ROOT

MM_PER_INCH = 25.4
PREVIEW_SIZE = (1000, 700)
RENDER_SHARPNESS = 2  # drawn this many times larger and shrunk, for smooth edges
VIEW = np.array((1, -1.6, 0.9))    # direction from the model to the camera
LIGHT = np.array((0.3, -1.6, 1.4))
MODEL_COLOUR = np.array((236, 228, 214))
BACKGROUND = (185, 185, 189)
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


def read_stl(path):
    """The corners of each triangle in a binary STL, as an array of shape (triangles, 3, 3)."""
    record = [("normal", "<f4", 3), ("corners", "<f4", (3, 3)), ("attribute", "<u2")]
    return np.fromfile(path, dtype=record, offset=84)["corners"].astype(float)


def split_long_triangles(triangles):
    """Split long triangles into four, because each is drawn in order of its average depth."""
    limit = np.ptp(triangles.reshape(-1, 3), axis=0).max() / 20
    for _ in range(4):
        edges = np.linalg.norm(triangles - np.roll(triangles, 1, axis=1), axis=2).max(axis=1)
        long = edges > limit
        a, b, c = (triangles[long, i] for i in range(3))
        ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        pieces = [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]
        triangles = np.concatenate([triangles[~long]] + [np.stack(p, axis=1) for p in pieces])
    return triangles


def render(triangles, path):
    """Draw a shaded picture of a mesh, nearest triangles last.

    This runs on the CPU because the app has to work on computers without OpenGL, such as virtual
    machines and remote desktops, where VTK crashes.
    """
    triangles = split_long_triangles(triangles)
    towards_camera = VIEW / np.linalg.norm(VIEW)
    right = np.cross((0, 0, 1), towards_camera)
    right /= np.linalg.norm(right)
    up = np.cross(towards_camera, right)

    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(lengths == 0, 1, lengths)
    facing = normals @ towards_camera

    x, y = triangles @ right, triangles @ up
    width, height = (size * RENDER_SHARPNESS for size in PREVIEW_SIZE)
    scale = 0.85 * min(width / np.ptp(x), height / np.ptp(y))
    x = (x - (x.min() + x.max()) / 2) * scale + width / 2
    y = height / 2 - (y - (y.min() + y.max()) / 2) * scale

    light = normals @ (LIGHT / np.linalg.norm(LIGHT))
    brightness = 0.35 + 0.65 * np.clip(light, 0, 1)
    colours = (np.outer(brightness, MODEL_COLOUR)).astype(int)

    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    depth = (triangles @ towards_camera).mean(axis=1)
    for i in np.argsort(depth):
        if facing[i] > 0:
            colour = tuple(colours[i].tolist())
            draw.polygon(list(zip(x[i].tolist(), y[i].tolist())), fill=colour, outline=colour)
    image.resize(PREVIEW_SIZE, Image.LANCZOS).save(path)


def report(out_dir):
    """Print the size of each part in both units and render the biggest one."""
    parts = {stl.name: read_stl(stl) for stl in sorted(out_dir.glob("*.stl"))}
    print("\nfinished parts:")
    for name, triangles in parts.items():
        size = np.ptp(triangles.reshape(-1, 3), axis=0)
        print(f"  {name}: {' x '.join(f'{v:.1f}' for v in size)} mm "
              f"({' x '.join(f'{v / MM_PER_INCH:.2f}' for v in size)} in)")
    biggest = max(parts.values(), key=lambda part: np.ptp(part.reshape(-1, 3), axis=0).prod())
    render(biggest, out_dir / "preview.png")


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


def main():
    sys.stdout.reconfigure(line_buffering=True)  # so the app's log shows progress as it happens
    print(READY, flush=True)
    for line in sys.stdin:
        print(f"{FINISHED} {run_job(json.loads(line))}", flush=True)


if __name__ == "__main__":
    main()
