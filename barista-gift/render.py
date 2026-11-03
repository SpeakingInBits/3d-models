"""Render preview images of the barista gift from the STLs in ./out."""

import sys
from pathlib import Path

import pyvista as pv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tip-cup-jar"))
from tip_cup import CUP_H  # noqa: E402
from render import shot  # noqa: E402  (tip-cup-jar/render.py)

OUT = Path(__file__).parent / "out"
CREAM, LID_PINK = "#ece4d6", "#c96f86"


def main():
    cup = pv.read(OUT / "cup.stl")
    lid = pv.read(OUT / "lid.stl")  # stored top-down for printing; flip back
    lid = lid.rotate_x(180, inplace=False)
    lid = lid.translate((0, 0, CUP_H - lid.bounds[4]), inplace=False)
    parts = [(cup, CREAM), (lid, LID_PINK)]
    c = (0, 0, 70)
    shot(parts, OUT / "preview_front.png", [(0, -480, 130), c, (0, 0, 1)])
    shot(parts, OUT / "preview_angle.png", [(300, -380, 230), c, (0, 0, 1)])
    shot(parts, OUT / "preview_side.png", [(480, -60, 130), c, (0, 0, 1)])
    shot(parts, OUT / "preview_back.png", [(-200, 440, 180), c, (0, 0, 1)])
    shot([(lid, LID_PINK)], OUT / "preview_lid_top.png",
         [(0, -120, CUP_H + 320), (0, 0, CUP_H + 30), (0, 0, 1)])
    print("rendered previews to", OUT)


if __name__ == "__main__":
    main()
