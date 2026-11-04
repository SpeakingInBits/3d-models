"""Builds every model with the packaged worker, because a library missing from the package only
shows up when a model is built.

    python packaging/smoke_test.py <folder with ModelWorker.exe> <empty folder for the builds>
"""

import subprocess
import sys
from json import dumps
from pathlib import Path


def main():
    app, builds = Path(sys.argv[1]), Path(sys.argv[2])
    scripts = [script for folder in sorted((app / "_internal" / "models").iterdir())
               for script in folder.glob("*.py")]
    if not scripts:
        sys.exit(f"No models found in {app}.")

    worker = subprocess.Popen([app / "ModelWorker.exe"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    failed = []
    for script in scripts:
        folder = builds / script.parent.name
        folder.mkdir(parents=True)
        (folder / "parameters.json").write_text("{}", encoding="utf-8")
        worker.stdin.write(dumps({"script": str(script), "folder": str(folder)}) + "\n")
        worker.stdin.flush()

        for line in worker.stdout:
            print(line, end="", flush=True)
            if line.startswith("@@finished"):
                break
        else:
            sys.exit(f"The worker stopped during {script.name}, with exit code {worker.wait()}.")
        if not line.startswith("@@finished 0") or not list(folder.glob("*.stl")):
            failed.append(script.name)

    worker.stdin.close()
    worker.wait()
    if failed:
        sys.exit(f"These didn't build: {', '.join(failed)}")
    print(f"All {len(scripts)} models built.")


if __name__ == "__main__":
    main()
