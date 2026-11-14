"""A window that shows a model's parts in 3D, to turn around and look at from any side.

Drag to turn the part, drag with the right or middle button to move it, and scroll to zoom. It
follows the main window: picking another model shows that one, and a rebuild shows the new parts
without moving the view.
"""

import tkinter as tk
from tkinter import ttk

import numpy as np
from PIL import Image, ImageTk

from mesh import Camera, Mesh, read_stl, render

MM_PER_INCH = 25.4
DEGREES_PER_PIXEL = 0.4
ZOOM_STEP = 1.15         # per notch of the mouse wheel
SHARPEN_DELAY_MS = 120   # after the view stops moving, it's redrawn larger and shrunk for smooth edges
SHARPNESS = 2
VIEWS = {               # yaw, pitch
    "Front": (0, -90), "Back": (180, -90), "Left": (90, -90), "Right": (-90, -90),
    "Top": (0, 0), "Bottom": (0, -180), "Angle": (Camera.yaw, Camera.pitch),
}


def part_files(folder):
    """The STL files in a folder, biggest first, because that's usually the main part."""
    if not folder or not folder.is_dir():
        return []
    return sorted(folder.glob("*.stl"), key=lambda path: (-path.stat().st_size, path.name))


class Viewer:
    def __init__(self, parent, scale):
        self.window = tk.Toplevel(parent)
        self.window.title("3D view")
        self.window.geometry(f"{int(900 * scale)}x{int(760 * scale)}")
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=1)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.closed = False
        self.camera = Camera()
        self.meshes = {}        # STL path -> (modified time, Mesh)
        self.folder = None
        self.title = ""
        self.mesh = None
        self.photo = None
        self.drag = None        # (button, x, y) while dragging
        self.redraw_pending = None
        self.sharpen_pending = None

        bar = ttk.Frame(self.window, padding=(8, 8, 8, 4))
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(2, weight=1)
        ttk.Label(bar, text="Part").grid(row=0, column=0, padx=(0, 6))
        self.part = ttk.Combobox(bar, state="readonly", width=24)
        self.part.grid(row=0, column=1)
        self.part.bind("<<ComboboxSelected>>", lambda _: self.load_part())
        self.size_label = ttk.Label(bar)
        self.size_label.grid(row=0, column=2, sticky="w", padx=12)
        views = ttk.Frame(bar)
        views.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))
        for name, (yaw, pitch) in VIEWS.items():
            ttk.Button(views, text=name, width=7,
                       command=lambda y=yaw, p=pitch: self.set_view(y, p)).pack(side="left", padx=(0, 4))
        ttk.Label(bar, text="Drag to turn  ·  right-drag to move  ·  scroll to zoom",
                  foreground="#6b6b6b").grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))

        self.canvas = tk.Canvas(self.window, highlightthickness=0, background="#b9b9bd")
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _: self.redraw())
        for button in (1, 2, 3):
            self.canvas.bind(f"<ButtonPress-{button}>", lambda e, b=button: self.start_drag(e, b))
            self.canvas.bind(f"<B{button}-Motion>", self.dragged)
            self.canvas.bind(f"<ButtonRelease-{button}>", self.end_drag)
        self.canvas.bind("<MouseWheel>", self.scrolled)
        self.canvas.bind("<Double-Button-1>", lambda _: self.set_view(*VIEWS["Angle"]))

    # ------------------------------------------------------------ what's shown
    def show(self, title, folder):
        """Show a model's parts. The view only resets when the model changes."""
        if title != self.title:
            self.camera = Camera()
        self.title, self.folder = title, folder
        self.window.title(f"3D view - {title}")
        files = part_files(folder)
        names = [path.name for path in files]
        current = self.part.get()
        self.part.configure(values=names)
        self.part.set(current if current in names else (names[0] if names else ""))
        self.load_part()

    def load_part(self):
        name = self.part.get()
        path = self.folder / name if self.folder and name else None
        self.mesh = None
        if path and path.exists():
            modified = path.stat().st_mtime
            cached = self.meshes.get(path)
            if cached and cached[0] == modified:
                self.mesh = cached[1]
            else:
                try:
                    self.mesh = Mesh(read_stl(path))
                    self.meshes[path] = (modified, self.mesh)
                except (OSError, ValueError, IndexError):
                    self.mesh = None
        if self.mesh is None:
            self.size_label.configure(text="No parts to show")
        else:
            mm = self.mesh.size
            self.size_label.configure(
                text=f"{' x '.join(f'{v:.1f}' for v in mm)} mm   "
                     f"({' x '.join(f'{v / MM_PER_INCH:.2f}' for v in mm)} in)")
        self.redraw()

    # ------------------------------------------------------------ drawing
    def redraw(self, sharp=False):
        """Draw at screen size now, and again sharper once the view has stopped moving."""
        if self.closed:
            return
        for pending in (self.redraw_pending, self.sharpen_pending):
            if pending:
                self.window.after_cancel(pending)
        self.redraw_pending = self.sharpen_pending = None
        if not sharp:
            # drawing waits for the window to be idle, so a fast drag skips frames instead of lagging
            self.redraw_pending = self.window.after_idle(self.draw, 1)
        self.sharpen_pending = self.window.after(SHARPEN_DELAY_MS, self.draw, SHARPNESS)

    def draw(self, sharpness):
        if sharpness == 1:
            self.redraw_pending = None
        else:
            self.sharpen_pending = None
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width < 2 or height < 2:
            return
        self.canvas.delete("all")
        if self.mesh is None:
            self.canvas.create_text(width / 2, height / 2, text="No parts to show",
                                    fill="#555555", font=("Segoe UI", 11))
            return
        pixels = render(self.mesh, self.camera, width * sharpness, height * sharpness)
        image = Image.fromarray(pixels)
        if sharpness > 1:
            image = image.resize((width, height), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")

    # ------------------------------------------------------------ mouse
    def set_view(self, yaw, pitch):
        self.camera = Camera(yaw=yaw, pitch=pitch)
        self.redraw()

    def start_drag(self, event, button):
        self.drag = (button, event.x, event.y)

    def dragged(self, event):
        if not self.drag or self.mesh is None:
            return
        button, x, y = self.drag
        dx, dy = event.x - x, event.y - y
        self.drag = (button, event.x, event.y)
        if button == 1:
            self.camera.yaw += dx * DEGREES_PER_PIXEL
            self.camera.pitch = float(np.clip(self.camera.pitch + dy * DEGREES_PER_PIXEL, -180, 0))
        else:
            scale = self.camera.pixels_per_mm(self.mesh, *self.canvas_size())
            self.camera.pan_x += dx / scale
            self.camera.pan_y -= dy / scale
        self.redraw()

    def end_drag(self, _event):
        self.drag = None

    def scrolled(self, event):
        """Zoom about the point under the mouse, so it stays where it is."""
        if self.mesh is None:
            return
        width, height = self.canvas_size()
        before = self.camera.pixels_per_mm(self.mesh, width, height)
        self.camera.zoom = float(np.clip(self.camera.zoom * ZOOM_STEP ** (event.delta / 120), 0.2, 40))
        after = self.camera.pixels_per_mm(self.mesh, width, height)
        across, up = event.x - width / 2, height / 2 - event.y
        self.camera.pan_x += across / after - across / before
        self.camera.pan_y += up / after - up / before
        self.redraw()

    def canvas_size(self):
        return self.canvas.winfo_width(), self.canvas.winfo_height()

    # ------------------------------------------------------------ window
    def lift(self):
        if self.window.state() == "iconic":
            self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def close(self):
        self.closed = True
        self.window.destroy()
