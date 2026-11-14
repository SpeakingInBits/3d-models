"""Pick a model, fill out its parameters in millimetres or inches, and see it rebuild as you type.

    .venv/Scripts/python configurator/app.py

Saved builds go to a new folder under custom-builds, so the models' own files are never changed.
"""

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import ttk

from tkinterdnd2 import TkinterDnD

from models import FROZEN, ROOT, Model, find_models
from stickers import StickerEditor, read_stickers, write_templates
from updates import Updater, run_install_hooks

MM_PER_INCH = 25.4
# updates replace the installed app's folder, so an installed copy keeps its files in Documents
BUILDS = Path.home() / "Documents" / "3D Model Configurator" if FROZEN else ROOT / "custom-builds"
PREVIEWS = BUILDS / ".preview"
SETTINGS = BUILDS / "settings.json"
WORKER_COMMAND = ([str(Path(sys.executable).with_name("ModelWorker.exe"))] if FROZEN else
                  [sys.executable, str(Path(__file__).with_name("build_model.py"))])
READY, FINISHED = "@@ready", "@@finished"  # as in build_model.py, which is slow to import
PREVIEW_DELAY_MS = 600   # how long typing has to pause before a rebuild starts
UNITS = {"angle": "°", "ratio": "", "count": ""}
NOTE_COLOUR = "#6b6b6b"


def load_settings():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def show(value, decimals=3):
    if isinstance(value, float):
        return f"{value:.{decimals}f}".rstrip("0").rstrip(".")
    return str(value)


class Field:
    """One row of the form. Length rows have a mm box and an inch box that stay in step."""

    def __init__(self, parent, row, param, note_width, on_change):
        self.param = param
        self.syncing = False
        self.entry = None
        ttk.Label(parent, text=param.label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=2)

        if param.kind == "flag":
            self.var = tk.BooleanVar(value=param.default)
            ttk.Checkbutton(parent, variable=self.var).grid(row=row, column=1, sticky="w")
        elif param.kind == "text":
            self.var = tk.StringVar(value=param.default)
            self.entry = ttk.Entry(parent, textvariable=self.var)
            self.entry.grid(row=row, column=1, columnspan=4, sticky="ew")
        else:
            self.var = tk.StringVar(value=show(param.default))
            self.entry = ttk.Entry(parent, textvariable=self.var, width=9, justify="right")
            self.entry.grid(row=row, column=1)
            unit = "mm" if param.kind == "length" else UNITS[param.kind]
            ttk.Label(parent, text=unit).grid(row=row, column=2, sticky="w", padx=(3, 10))

        if param.kind == "length":
            self.inches = tk.StringVar(value=show(param.default / MM_PER_INCH))
            ttk.Entry(parent, textvariable=self.inches, width=9, justify="right").grid(row=row, column=3)
            ttk.Label(parent, text="in").grid(row=row, column=4, sticky="w", padx=(3, 10))
            self.link(self.var, self.inches, 1 / MM_PER_INCH)
            self.link(self.inches, self.var, MM_PER_INCH)

        ttk.Label(parent, text=param.note, foreground=NOTE_COLOUR, wraplength=note_width).grid(
            row=row, column=5, sticky="w", padx=(6, 0))
        self.default_value = self.var.get()
        self.var.trace_add("write", lambda *_: on_change())

    def link(self, source, target, factor):
        def changed(*_):
            if self.syncing:
                return
            self.syncing = True
            try:
                target.set(show(float(source.get()) * factor))
            except ValueError:
                target.set("")
            self.syncing = False
        source.trace_add("write", changed)

    def reset(self):
        self.var.set(self.default_value)

    def change(self):
        """The new value, or None if it is still the default. Raises ValueError if it isn't valid."""
        current = self.var.get()
        if current == self.default_value:
            return None
        if self.param.kind == "count":
            return int(current)
        if self.param.kind in ("flag", "text"):
            return current
        return float(current)


class Worker:
    """A build process that has the CAD libraries loaded and is waiting for a job."""

    def __init__(self, lines):
        self.ready = False
        self.stopped = False
        self.process = subprocess.Popen(
            WORKER_COMMAND, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        threading.Thread(target=self.read_output, args=(lines,), daemon=True).start()

    def read_output(self, lines):
        for line in self.process.stdout:
            lines.put((self, line))
        lines.put((self, None))

    def send(self, job):
        self.process.stdin.write(json.dumps(job) + "\n")
        self.process.stdin.flush()

    def stop(self):
        self.stopped = True
        self.process.kill()
        self.process.wait()


@dataclass
class Job:
    model: Model
    folder: Path
    saving: bool  # True for a saved build, False for a preview


class App:
    def __init__(self, root):
        self.root = root
        self.models = find_models()
        self.forms = {}         # model key -> (frame, fields)
        self.latest = {}        # model key -> folder of its latest saved build
        self.shown = {}         # model key -> folder of the build in the picture
        self.previewed = {}     # model key -> the changes last sent to be built
        self.failed = set()     # keys of models whose latest build didn't finish
        self.job = None
        self.pending = None     # the timer waiting for typing to pause
        self.image = None
        self.lines = queue.Queue()
        # with a spare, a change can kill the running job and start at once. Without one, it waits
        # for that job to finish, because loading a new worker would take longer. The spare starts
        # loading once the first worker is ready, so that the two don't slow each other down.
        self.use_spare = tk.BooleanVar(value=load_settings().get("spare_worker", False))
        self.worker = Worker(self.lines)
        self.spare = None
        self.scale = root.winfo_fpixels("1i") / 96  # 2 on a display scaled to 200%
        self.updater = Updater()

        version = self.updater.version
        root.title(f"3D Model Configurator {version}" if version else "3D Model Configurator")
        if FROZEN:
            root.iconbitmap(default=sys.executable)
        width = min(int(1360 * self.scale), root.winfo_screenwidth() - 40)
        height = min(int(800 * self.scale), root.winfo_screenheight() - 120)
        root.geometry(f"{width}x{height}+20+20")
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.build_menu()
        self.build_list()
        self.build_form_area()
        self.build_side_panel()
        self.model_list.selection_set(0)
        self.select_model()
        self.updater.check_in_background()
        self.poll()

    # ------------------------------------------------------------ layout
    def build_menu(self):
        menu_bar = tk.Menu(self.root, tearoff=False)
        settings = tk.Menu(menu_bar, tearoff=False)
        settings.add_checkbutton(
            label="Keep a spare worker (faster edits during a rebuild, about 350 MB more memory)",
            variable=self.use_spare, command=self.spare_setting_changed)
        menu_bar.add_cascade(label="Settings", menu=settings)
        self.root.configure(menu=menu_bar)

    def build_list(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=0, sticky="ns")
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Models", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")
        self.model_list = tk.Listbox(frame, width=30, exportselection=False, activestyle="none",
                                     font=("Segoe UI", 10))
        self.model_list.grid(row=1, column=0, sticky="ns", pady=(6, 0))
        for model in self.models:
            self.model_list.insert("end", model.title)
        self.model_list.bind("<<ListboxSelect>>", self.select_model)

    def build_form_area(self):
        frame = ttk.Frame(self.root, padding=(0, 10))
        frame.grid(row=0, column=1, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        self.summary = ttk.Label(frame, wraplength=int(600 * self.scale), justify="left")
        self.summary.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.canvas = tk.Canvas(frame, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, command=self.canvas.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.holder = ttk.Frame(self.canvas)
        self.canvas.create_window(0, 0, window=self.holder, anchor="nw")
        self.holder.bind("<Configure>", lambda _: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind_all("<MouseWheel>", self.scroll)

    def build_side_panel(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=2, sticky="ns")
        frame.rowconfigure(4, weight=1)
        self.picture_title = ttk.Label(frame, font=("Segoe UI", 10, "bold"))
        self.picture_title.grid(row=0, column=0, sticky="w")
        self.picture = ttk.Label(frame)
        self.picture.grid(row=1, column=0, pady=(4, 8))

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, sticky="ew")
        self.save_button = ttk.Button(buttons, text="Save build", command=self.save_build)
        self.cancel_button = ttk.Button(buttons, text="Cancel", command=self.cancel_job,
                                        state="disabled")
        self.reset_button = ttk.Button(buttons, text="Reset to defaults", command=self.reset)
        self.folder_button = ttk.Button(buttons, text="Open build folder", command=self.open_folder,
                                        state="disabled")
        self.sticker_button = ttk.Button(buttons, text="Make stickers", command=self.open_stickers,
                                         state="disabled")
        for column, button in enumerate((self.save_button, self.cancel_button, self.reset_button,
                                         self.folder_button, self.sticker_button)):
            button.grid(row=0, column=column, padx=(0, 6))

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.grid(row=3, column=0, sticky="ew", pady=8)
        self.log = tk.Text(frame, width=62, height=12, state="disabled", wrap="word",
                           font=("Consolas", 9))
        self.log.grid(row=4, column=0, sticky="nsew")
        self.update_button = ttk.Button(frame, command=self.install_update)  # shown once downloaded

    def scroll(self, event):
        if self.canvas.yview() != (0.0, 1.0):
            self.canvas.yview_scroll(-event.delta // 120, "units")

    def make_form(self, model):
        frame = ttk.Frame(self.holder, padding=(0, 0, 12, 0))
        frame.columnconfigure(5, weight=1)
        fields, section, row = [], None, 0
        for param in model.params:
            if param.section != section:
                section = param.section
                ttk.Label(frame, text=section, font=("Segoe UI", 10, "bold")).grid(
                    row=row, column=0, columnspan=6, sticky="w", pady=(12 if row else 0, 3))
                row += 1
            fields.append(Field(frame, row, param, int(300 * self.scale), self.schedule_preview))
            row += 1
        return frame, fields

    # ------------------------------------------------------------ form
    @property
    def model(self):
        return self.models[self.model_list.curselection()[0]]

    def select_model(self, _event=None):
        if not self.model_list.curselection():
            return
        model = self.model
        for frame, _ in self.forms.values():
            frame.pack_forget()
        if model.key not in self.forms:
            self.forms[model.key] = self.make_form(model)
        self.forms[model.key][0].pack(fill="both", expand=True)
        self.canvas.yview_moveto(0)
        self.summary.configure(text=model.summary)
        self.refresh_side_panel()
        self.update_preview()

    def refresh_side_panel(self):
        key = self.model.key
        build = self.shown.get(key)
        path = build / "preview.png" if build else self.model.preview
        shrink = 1 if self.scale >= 1.5 else 2
        self.image = tk.PhotoImage(file=path).subsample(shrink) if path else None
        self.picture.configure(image=self.image or "", text="" if path else "No preview yet")

        title = "Your changes" if build else "Default model"
        updating = self.job and self.job.model.key == key
        if updating:
            title += " (updating...)"
        elif key in self.failed:
            title += " (latest changes didn't build)"
        self.picture_title.configure(text=title)
        self.folder_button.configure(state="normal" if key in self.latest else "disabled")
        # the sizes aren't known while a build is running or after one has failed
        can_make = self.stickers() and not updating and key not in self.failed
        self.sticker_button.configure(state="normal" if can_make else "disabled")

    def stickers(self):
        """The sticker sizes of the build in the picture, or of the default model."""
        build = self.shown.get(self.model.key)
        return read_stickers(build / "stickers.json" if build else self.model.stickers_file)

    def open_stickers(self):
        StickerEditor(self.root, self.model, self.stickers(), BUILDS / "stickers" / self.model.key,
                      self.scale)

    def reset(self):
        for field in self.forms[self.model.key][1]:
            field.reset()

    def collect_changes(self):
        changes = {}
        for field in self.forms[self.model.key][1]:
            try:
                value = field.change()
            except ValueError:
                kind = "whole number" if field.param.kind == "count" else "number"
                self.write(f"{field.param.label} needs to be a {kind}.\n", clear=True)
                return None
            if value is not None:
                changes[field.param.name] = value
        return changes

    # ------------------------------------------------------------ builds
    def schedule_preview(self):
        if self.pending:
            self.root.after_cancel(self.pending)
        self.pending = self.root.after(PREVIEW_DELAY_MS, self.update_preview)

    def update_preview(self):
        """Rebuild the current model if its form no longer matches what was last built."""
        self.pending = None
        model = self.model
        changes = self.collect_changes()
        if changes is None or changes == self.previewed.get(model.key, {}):
            return
        if self.job and (self.job.saving or not self.use_spare.get()):
            return  # finish_job comes back here
        if changes:
            self.start_job(model, changes, PREVIEWS / model.key, saving=False)
            return
        self.stop_job()
        self.previewed[model.key] = changes
        self.shown.pop(model.key, None)
        self.failed.discard(model.key)
        self.write("", clear=True)
        self.refresh_side_panel()

    def save_build(self):
        changes = self.collect_changes()
        if changes is None:
            return
        model = self.model
        folder = BUILDS / model.key / datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.start_job(model, changes, folder, saving=True)

    def start_job(self, model, changes, folder, saving):
        self.stop_job()
        if self.pending:
            self.root.after_cancel(self.pending)
            self.pending = None
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "parameters.json").write_text(json.dumps(changes, indent=2), encoding="utf-8")
        self.previewed[model.key] = changes
        self.job = Job(model, folder, saving)
        self.worker.send({"script": str(model.script), "folder": str(folder)})

        verb = "Saving" if saving else "Updating"
        self.write(f"{verb} {model.title}, {len(changes)} parameter(s) changed...\n", clear=True)
        can_save = not saving and self.use_spare.get()  # saving would have to replace this job
        self.save_button.configure(state="normal" if can_save else "disabled")
        self.cancel_button.configure(state="normal")
        self.progress.start(12)
        self.refresh_side_panel()

    def stop_job(self, rebuild_later=True):
        """Kill the running job, if any, and move on to the spare worker."""
        if not self.job:
            return
        if rebuild_later:
            self.previewed.pop(self.job.model.key, None)
        self.job = None
        self.replace_worker()
        self.set_idle()

    def replace_worker(self):
        self.worker.stop()
        self.worker, self.spare = self.spare or Worker(self.lines), None
        self.add_spare()

    def add_spare(self):
        if self.use_spare.get() and self.worker.ready and not self.spare:
            self.spare = Worker(self.lines)

    def spare_setting_changed(self):
        BUILDS.mkdir(exist_ok=True)
        SETTINGS.write_text(json.dumps({"spare_worker": self.use_spare.get()}), encoding="utf-8")
        if self.use_spare.get():
            self.add_spare()
        elif self.spare:
            self.spare.stop()
            self.spare = None

    def set_idle(self):
        self.progress.stop()
        self.save_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")

    def cancel_job(self):
        job = self.job
        if job:
            self.stop_job(rebuild_later=False)
            if job.saving:
                shutil.rmtree(job.folder, ignore_errors=True)
            self.write("\nCancelled.\n")
            self.refresh_side_panel()

    def poll(self):
        try:
            while True:
                worker, line = self.lines.get_nowait()
                if line is None:
                    self.worker_ended(worker)
                elif line.startswith(READY):
                    worker.ready = True
                    self.add_spare()
                elif worker is self.worker and self.job:
                    if line.startswith(FINISHED):
                        self.finish_job(int(line.split()[1]))
                    else:
                        self.write(line)
        except queue.Empty:
            pass
        if self.updater.update and not self.update_button.winfo_ismapped():
            self.update_button.configure(
                text=f"Restart now to update to version {self.updater.new_version}")
            self.update_button.grid(row=5, column=0, sticky="ew", pady=(8, 0))
            self.bring_to_front()
        self.root.after(50, self.poll)

    def bring_to_front(self):
        """Raises the window over the others, so the update button isn't hidden behind them."""
        if self.root.state() == "iconic":
            self.root.deiconify()
        self.root.lift()
        # Windows won't raise a window that isn't active above the others; staying on top for a
        # moment gets around that without taking the keyboard from whatever the person is typing in.
        self.root.attributes("-topmost", True)
        self.root.after(200, self.root.attributes, "-topmost", False)

    def install_update(self):
        self.stop_workers()
        self.updater.restart()

    def worker_ended(self, worker):
        """A worker that wasn't stopped crashed, which bad geometry can do to the CAD kernel."""
        if worker.stopped:
            return
        if worker is self.spare:
            self.spare = None
            self.add_spare()
        elif worker is self.worker:
            self.replace_worker()
            if self.job:
                self.write("\nThe CAD kernel crashed on these values.\n")
                self.finish_job(1)

    def finish_job(self, code):
        job, self.job = self.job, None
        key = job.model.key
        self.set_idle()
        if code == 0:
            self.shown[key] = job.folder
            self.failed.discard(key)
            if job.saving:
                self.latest[key] = job.folder
                self.write(f"\nSaved to {job.folder}\n")
                self.save_templates(job.folder)
        else:
            self.failed.add(key)
            if job.saving:
                shutil.rmtree(job.folder, ignore_errors=True)
            self.write("\nThe build did not finish. The last lines above say why.\n")
        self.refresh_side_panel()
        self.update_preview()

    def save_templates(self, folder):
        try:
            names = write_templates(folder)
        except OSError as error:
            self.write(f"The Photoshop templates couldn't be saved: {error}\n")
            return
        if names:
            self.write(f"Photoshop templates: {', '.join(names)}\n")

    def open_folder(self):
        os.startfile(self.latest[self.model.key])

    def write(self, text, clear=False):
        self.log.configure(state="normal")
        if clear:
            self.log.delete("1.0", "end")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def stop_workers(self):
        self.worker.stop()
        if self.spare:
            self.spare.stop()

    def close(self):
        self.stop_workers()
        self.root.destroy()


def main():
    if FROZEN:
        run_install_hooks()
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # keeps text sharp on scaled displays
    except (AttributeError, ImportError, OSError):
        pass
    root = TkinterDnD.Tk()  # tk.Tk with drag and drop
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
