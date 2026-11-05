# PyInstaller build of the configurator, run by package.sh.
#
# Two programs share one folder. ModelConfigurator.exe is the window and opens quickly because it
# doesn't load the CAD libraries. ModelWorker.exe is the background worker that does, and it needs
# a console so that the window can talk to it, which the app keeps hidden.

import ast
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parent
PACKAGING = ROOT / "packaging"
CONFIGURATOR = ROOT / "configurator"
sys.path.insert(0, str(CONFIGURATOR))
from models import find_models  # noqa: E402

MODELS = find_models()


def imports_of(script):
    """Top-level modules a model imports. The worker loads models from text, so PyInstaller can't see them."""
    names = set()
    for node in ast.walk(ast.parse(script.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names.add(node.module)
    return names


local_modules = {model.script.stem for model in MODELS}
model_imports = sorted({name for model in MODELS for name in imports_of(model.script)} - local_modules)

model_files = []
for model in MODELS:
    folder = model.script.parent
    model_files += [(str(model.script), f"models/{folder.name}"),
                    (str(folder / "README.md"), f"models/{folder.name}")]
    if model.preview:
        model_files.append((str(model.preview), f"models/{folder.name}/out"))
    if model.stickers_file.exists():
        model_files.append((str(model.stickers_file), f"models/{folder.name}/out"))

worker_datas, worker_binaries, worker_imports = [], [], list(model_imports)
for package in ("build123d", "bd_warehouse", "lib3mf"):
    datas, binaries, imports = collect_all(package)
    worker_datas += datas
    worker_binaries += binaries
    worker_imports += imports

dnd_datas, dnd_binaries, dnd_imports = collect_all("tkinterdnd2")
app = Analysis([str(CONFIGURATOR / "app.py")], pathex=[str(CONFIGURATOR)],
               datas=model_files + dnd_datas, binaries=dnd_binaries, hiddenimports=dnd_imports)
worker = Analysis([str(CONFIGURATOR / "build_model.py")], pathex=[str(CONFIGURATOR)],
                  datas=worker_datas, binaries=worker_binaries, hiddenimports=worker_imports,
                  # jedi's deep folders can pass Windows' path length limit when installed
                  excludes=["tkinter", "jedi"])

icon = str(PACKAGING / "app-icon" / "icon.ico")
app_exe = EXE(PYZ(app.pure), app.scripts, exclude_binaries=True, name="ModelConfigurator",
              console=False, icon=icon)
worker_exe = EXE(PYZ(worker.pure), worker.scripts, exclude_binaries=True, name="ModelWorker",
                 console=True, icon=icon)
COLLECT(app_exe, app.binaries, app.datas, worker_exe, worker.binaries, worker.datas,
        name="ModelConfigurator")
