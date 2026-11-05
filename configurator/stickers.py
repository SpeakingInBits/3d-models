"""Turn a photo into a sticker that fits a model's recess, ready for Cricut Print Then Cut.

Models with sticker spots write their sizes to stickers.json when they build. Drop a photo on the
editor, move, resize and rotate it, and export a PNG. The PNG is the exact size of the sticker at
300 DPI with transparent corners, which Cricut Design Space turns into the cut line.

Saved builds also get a Photoshop template for each sticker size, so the size of the stickers for
a printed model is still on file after the model's settings have moved on.
"""

import json
import tkinter as tk
from dataclasses import dataclass
from math import cos, radians, sin
from pathlib import Path
from struct import pack
from tkinter import filedialog, ttk

from PIL import Image, ImageDraw, ImageOps, ImageTk
from pillow_heif import register_heif_opener
from psd_tools import PSDImage
from psd_tools.constants import Resource
from psd_tools.psd.image_resources import ImageResource
from tkinterdnd2 import DND_FILES

register_heif_opener()  # iPhones save photos as HEIC

DPI = 300
MM_PER_INCH = 25.4
SHARPNESS = 2            # exports are drawn this many times larger and shrunk, for smooth edges
PROXY_SIZE = 1600        # the longest side of the copy of the photo used while editing
VIEW_SIZE = (520, 560)
VIEW_ROOM = 330          # height of everything but the view, with the window frame and taskbar
VIEW_FILL = 0.75         # how much of the view the sticker takes up
OUTSIDE_COLOUR = "#8c8c8c"
OUTSIDE_FADE = 0.7       # how faded the part of the photo outside the sticker is
OUTLINE_COLOUR = "#2f6fde"
SIZE_RANGE = (10, 400)   # percent of the size that fills the sticker
WHEEL_STEP = 1.05
PHOTO_TYPES = "*.jpg *.jpeg *.png *.heic *.heif *.webp *.bmp *.tif *.tiff"


@dataclass
class Sticker:
    name: str
    width: float   # all in millimetres
    height: float
    corner: float
    count: int

    @property
    def label(self):
        name = self.name[0].upper() + self.name[1:]
        return f"{name}: {self.width:g} x {self.height:g} mm ({self.count} needed)"

    @property
    def file_name(self):
        """Has the size in it, so that it stays with the sticker's files wherever they end up."""
        return f"{self.name.lower().replace(' ', '-')}-{self.width:g}x{self.height:g}mm"

    @property
    def pixels(self):
        return round(self.width / MM_PER_INCH * DPI), round(self.height / MM_PER_INCH * DPI)


@dataclass
class Placement:
    """Where the photo sits, in millimetres from the middle of the sticker with y going down."""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0   # of the photo, before it's rotated
    angle: float = 0.0   # degrees clockwise


def read_stickers(path):
    if not path.exists():
        return []
    return [Sticker(**sticker) for sticker in json.loads(path.read_text(encoding="utf-8"))]


def fill_width(photo, sticker, angle):
    """The photo width that just covers the whole sticker at this angle."""
    c, s = abs(cos(radians(angle))), abs(sin(radians(angle)))
    return photo.width * max((sticker.width * c + sticker.height * s) / photo.width,
                             (sticker.width * s + sticker.height * c) / photo.height)


def fit_width(photo, sticker, angle):
    """The photo width that just shows the whole photo inside the sticker at this angle."""
    c, s = abs(cos(radians(angle))), abs(sin(radians(angle)))
    return photo.width * min(sticker.width / (photo.width * c + photo.height * s),
                             sticker.height / (photo.width * s + photo.height * c))


def paint(photo, placement, size, px_per_mm):
    """A transparent image of the given size with the photo placed around its middle."""
    scale = placement.width * px_per_mm / photo.width
    if scale < 0.5:  # shrink first, because a transform alone would skip pixels and look rough
        photo = photo.reduce(int(1 / scale))
        scale = placement.width * px_per_mm / photo.width

    # each output pixel looks up its source pixel, so this is the placement backwards
    centre_x = size[0] / 2 + placement.x * px_per_mm
    centre_y = size[1] / 2 + placement.y * px_per_mm
    c, s = cos(radians(placement.angle)) / scale, sin(radians(placement.angle)) / scale
    return photo.transform(size, Image.AFFINE,
                           (c, s, photo.width / 2 - c * centre_x - s * centre_y,
                            -s, c, photo.height / 2 + s * centre_x - c * centre_y),
                           resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))


def rounded_mask(size, box, radius):
    """A mask of a rounded rectangle, with smooth corners."""
    big = Image.new("L", [side * 4 for side in size], 0)
    ImageDraw.Draw(big).rounded_rectangle([value * 4 for value in box], radius * 4, fill=255)
    return big.resize(size, Image.LANCZOS)


def render_sticker(photo, placement, sticker):
    """The finished sticker at print size. Paper shows anywhere the photo doesn't cover."""
    size = sticker.pixels
    big_size = size[0] * SHARPNESS, size[1] * SHARPNESS
    image = Image.new("RGBA", big_size, "white")
    image.alpha_composite(paint(photo, placement, big_size, DPI / MM_PER_INCH * SHARPNESS))
    image = image.resize(size, Image.LANCZOS)
    radius = sticker.corner / MM_PER_INCH * DPI
    image.putalpha(rounded_mask(size, (0, 0, *size), radius))
    return image


def write_template(sticker, path):
    """A Photoshop file at print size, with a group masked to the sticker's shape."""
    size = sticker.pixels
    # RGBA as an RGB document would turn the clear layer into a solid one behind a black mask
    psd = PSDImage.new("RGBA", size, color=(0, 0, 0, 0))
    # without this it opens at 72 DPI, about four times too big. The DPI is in 16.16 fixed point,
    # and the 1s mean pixels per inch and sizes shown in inches, as Photoshop writes them
    resolution = pack(">I2HI2H", DPI << 16, 1, 1, DPI << 16, 1, 1)
    psd.image_resources[Resource.RESOLUTION_INFO] = ImageResource(key=Resource.RESOLUTION_INFO,
                                                                  data=resolution)
    group = psd.create_group(name=f"Sticker {sticker.width:g} x {sticker.height:g} mm "
                                  "(design inside this group)")
    group.create_pixel_layer(Image.new("RGB", size, "white"), name="Background colour")
    group.create_pixel_layer(Image.new("RGBA", size, (0, 0, 0, 0)),
                             name="Your design (place artwork here)")
    psd.save(path)

    # a new group's two records share their channels, so a mask added now corrupts the file. Ones
    # read from a file don't
    psd = PSDImage.open(path)
    radius = sticker.corner / MM_PER_INCH * DPI
    psd[0].create_mask(rounded_mask(size, (0, 0, *size), radius), top=0, left=0)
    psd.save(path)


def write_templates(folder):
    """A template for each sticker size in a build's folder. Returns the names of the files."""
    names = []
    for sticker in read_stickers(folder / "stickers.json"):
        names.append(f"{sticker.file_name}.psd")
        write_template(sticker, folder / names[-1])
    return names


class StickerEditor(tk.Toplevel):
    """Holds the rest of the app until it's closed, so the sticker sizes can't change under it."""

    def __init__(self, parent, model, stickers, folder, scale):
        super().__init__(parent)
        self.stickers = stickers
        self.sticker = stickers[0]
        self.folder = folder
        room = (self.winfo_screenheight() - VIEW_ROOM * scale) / VIEW_SIZE[1]
        self.view_size = tuple(int(side * min(scale, room)) for side in VIEW_SIZE)
        self.photo = None
        self.proxy = None
        self.photo_path = None
        self.placement = Placement()
        self.grabbed = None     # where the mouse was on the last drag
        self.view_image = None  # Tk only draws an image while something keeps hold of it

        self.title(f"Stickers for {model.title}")
        self.resizable(False, False)
        self.transient(parent)
        self.build_controls()
        self.use_sticker()
        self.grab_set()

    def build_controls(self):
        frame = ttk.Frame(self, padding=10)
        frame.grid()
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Sticker").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.picker = ttk.Combobox(frame, state="readonly",
                                   values=[sticker.label for sticker in self.stickers])
        self.picker.current(0)
        self.picker.grid(row=0, column=1, columnspan=2, sticky="ew")
        self.picker.bind("<<ComboboxSelected>>", self.pick_sticker)

        self.canvas = tk.Canvas(frame, width=self.view_size[0], height=self.view_size[1],
                                highlightthickness=0)
        self.canvas.grid(row=1, column=0, columnspan=3, pady=8)
        self.view_item = self.canvas.create_image(0, 0, anchor="nw")
        self.hint = self.canvas.create_text(self.view_size[0] / 2, self.view_size[1] / 2,
                                            text="Drop a photo here", fill="#6b6b6b",
                                            font=("Segoe UI", 12))
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<MouseWheel>", self.wheel)
        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind("<<Drop>>", self.drop)

        self.size = tk.DoubleVar(value=100)
        self.angle = tk.DoubleVar(value=0)
        self.size_text = tk.StringVar()
        self.angle_text = tk.StringVar()
        for row, (label, variable, limits, text, moved) in enumerate((
                ("Size", self.size, SIZE_RANGE, self.size_text, self.size_moved),
                ("Rotation", self.angle, (-180, 180), self.angle_text, self.angle_moved)), start=2):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8))
            ttk.Scale(frame, from_=limits[0], to=limits[1], variable=variable, command=moved).grid(
                row=row, column=1, sticky="ew", pady=2)
            ttk.Label(frame, textvariable=text, width=6, anchor="e").grid(row=row, column=2)

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        buttons.columnconfigure(4, weight=1)
        ttk.Button(buttons, text="Open photo", command=self.choose_photo).grid(row=0, column=0)
        self.edit_buttons = [
            ttk.Button(buttons, text="Fill sticker", command=self.fill),
            ttk.Button(buttons, text="Show whole photo", command=self.fit),
            ttk.Button(buttons, text="Rotate 90°", command=self.rotate_quarter),
            ttk.Button(buttons, text="Export PNG", command=self.export)]
        for column, button in enumerate(self.edit_buttons[:3], start=1):
            button.grid(row=0, column=column, padx=(6, 0))
        self.edit_buttons[3].grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(buttons, text="Export Photoshop template", command=self.export_template).grid(
            row=1, column=2, columnspan=2, sticky="ew", padx=(6, 0), pady=(6, 0))

        self.status = ttk.Label(frame, wraplength=self.view_size[0], justify="left")
        self.status.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))

    # ------------------------------------------------------------ photo
    def choose_photo(self):
        path = filedialog.askopenfilename(parent=self, title="Choose a photo",
                                          filetypes=[("Photos", PHOTO_TYPES), ("All files", "*")])
        if path:
            self.load(Path(path))

    def drop(self, event):
        self.load(Path(self.tk.splitlist(event.data)[0]))  # only the first of several files

    def load(self, path):
        try:
            with Image.open(path) as image:
                self.photo = ImageOps.exif_transpose(image).convert("RGBA")
        except (OSError, ValueError, Image.DecompressionBombError):
            self.status.configure(text=f"{path.name} couldn't be opened as a photo.")
            return
        self.photo_path = path
        self.proxy = self.photo.copy()
        self.proxy.thumbnail((PROXY_SIZE, PROXY_SIZE))
        self.status.configure(text="Drag to move. Scroll or use the sliders to resize and rotate.")
        self.canvas.itemconfigure(self.hint, state="hidden")
        self.canvas.configure(cursor="fleur")
        self.placement.angle = 0
        self.fill()

    def pick_sticker(self, _event):
        self.sticker = self.stickers[self.picker.current()]
        self.use_sticker()

    def use_sticker(self):
        """Work out the view for the current sticker, and fit the photo to it."""
        sticker, (width, height) = self.sticker, self.view_size
        self.px_per_mm = VIEW_FILL * min(width / sticker.width, height / sticker.height)
        half_w, half_h = sticker.width * self.px_per_mm / 2, sticker.height * self.px_per_mm / 2
        self.outline = (width / 2 - half_w, height / 2 - half_h,
                        width / 2 + half_w, height / 2 + half_h)
        self.shape = rounded_mask(self.view_size, self.outline, sticker.corner * self.px_per_mm)
        self.fill()

    # ------------------------------------------------------------ placing
    def fill(self):
        self.place_centred(fill_width)

    def fit(self):
        self.place_centred(fit_width)

    def place_centred(self, width_for):
        if self.photo:
            self.placement.x = self.placement.y = 0
            self.placement.width = width_for(self.photo, self.sticker, self.placement.angle)
        self.redraw()

    def full_size(self):
        """The photo width shown as 100%."""
        return fill_width(self.photo, self.sticker, 0)

    def rotate_quarter(self):
        self.placement.angle = (self.placement.angle + 270) % 360 - 180
        self.redraw()

    def size_moved(self, value):
        if self.photo:
            self.placement.width = float(value) / 100 * self.full_size()
            self.redraw()

    def angle_moved(self, value):
        if self.photo:
            self.placement.angle = float(value)
            self.redraw()

    def wheel(self, event):
        if self.photo:
            percent = self.placement.width / self.full_size() * 100
            percent *= WHEEL_STEP ** (event.delta / 120)
            self.size_moved(min(max(percent, SIZE_RANGE[0]), SIZE_RANGE[1]))
        return "break"  # or the app's form behind this window scrolls too

    def start_drag(self, event):
        self.grabbed = event.x, event.y

    def drag(self, event):
        if self.photo:
            self.placement.x += (event.x - self.grabbed[0]) / self.px_per_mm
            self.placement.y += (event.y - self.grabbed[1]) / self.px_per_mm
            self.grabbed = event.x, event.y
            self.redraw()

    # ------------------------------------------------------------ drawing
    def redraw(self):
        """Show the sticker in full, and the rest of the photo faded around it."""
        full = Image.new("RGBA", self.view_size, "white")
        if self.photo:
            full.alpha_composite(paint(self.proxy, self.placement, self.view_size, self.px_per_mm))
            self.size.set(self.placement.width / self.full_size() * 100)
            self.angle.set(self.placement.angle)
        faded = Image.blend(full, Image.new("RGBA", self.view_size, OUTSIDE_COLOUR), OUTSIDE_FADE)
        view = Image.composite(full, faded, self.shape)
        ImageDraw.Draw(view).rounded_rectangle(self.outline, self.sticker.corner * self.px_per_mm,
                                               outline=OUTLINE_COLOUR, width=2)
        self.view_image = ImageTk.PhotoImage(view)
        self.canvas.itemconfigure(self.view_item, image=self.view_image)
        self.size_text.set(f"{self.size.get():.0f}%")
        self.angle_text.set(f"{self.angle.get():.0f}°")
        for button in self.edit_buttons:
            button.configure(state="normal" if self.photo else "disabled")

    # ------------------------------------------------------------ export
    def ask_where(self, title, name, kind):
        self.folder.mkdir(parents=True, exist_ok=True)
        extension = Path(name).suffix
        path = filedialog.asksaveasfilename(
            parent=self, title=title, initialdir=self.folder, initialfile=name,
            defaultextension=extension, filetypes=[(kind, f"*{extension}")])
        return Path(path) if path else None

    def export(self):
        name = f"{self.sticker.file_name}-{self.photo_path.stem}.png"
        path = self.ask_where("Export sticker", name, "PNG image")
        if path:
            self.save(path)

    def export_template(self):
        path = self.ask_where("Export Photoshop template", f"{self.sticker.file_name}.psd",
                              "Photoshop file")
        if path:
            self.save_template(path)

    def save(self, path):
        try:
            render_sticker(self.photo, self.placement, self.sticker).save(path, dpi=(DPI, DPI))
        except OSError as error:
            self.status.configure(text=f"The sticker couldn't be saved: {error}")
            return
        self.status.configure(text=f"Saved {path.name}. In Cricut Design Space, upload it as a "
                                   f"Print Then Cut image and set its width to "
                                   f"{self.sticker.width:g} mm.")

    def save_template(self, path):
        try:
            write_template(self.sticker, path)
        except OSError as error:
            self.status.configure(text=f"The template couldn't be saved: {error}")
            return
        self.status.configure(text=f"Saved {path.name}. It opens in Photoshop at "
                                   f"{self.sticker.width:g} x {self.sticker.height:g} mm.")
