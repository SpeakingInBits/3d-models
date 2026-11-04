"""Draws the app's icon, a shaded cube, to icon.ico next to this file.

    .venv/Scripts/python packaging/app-icon/render_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

SCALE = 4  # drawn large and shrunk, for smooth edges
SIZE = 256 * SCALE
TOP, LEFT, RIGHT = "#e8934f", "#c96a2b", "#a4521d"


def point(x, y):
    return (x * SCALE, y * SCALE)


def main():
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.polygon([point(128, 20), point(232, 76), point(128, 132), point(24, 76)], fill=TOP)
    draw.polygon([point(24, 76), point(128, 132), point(128, 240), point(24, 184)], fill=LEFT)
    draw.polygon([point(232, 76), point(128, 132), point(128, 240), point(232, 184)], fill=RIGHT)
    image = image.resize((256, 256), Image.LANCZOS)
    image.save(Path(__file__).with_name("icon.ico"),
               sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
