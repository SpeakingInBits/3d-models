"""Sticker stand: a desktop stand shaped like an upside-down T, with a flat base and a vertical
wall that has recessed sticker spots on both its front and back.

All dimensions are in millimetres. Change the parameters below and re-run from the repo root:

    .venv/Scripts/python sticker-stand/sticker_stand.py

Outputs go to sticker-stand/out:
    stand.stl           - print flat on its base, no supports
    sticker_stand.step  - the stand, for viewing/editing in other CAD tools
    stickers.json       - sticker sizes for the configurator's sticker editor

Axes: X runs left to right, Y from front to back, Z up.
"""

import json
from pathlib import Path

from build123d import (
    Axis, Plane, Pos, Rectangle, RectangleRounded, chamfer, export_step, export_stl, extrude,
    fillet,
)

# ---------------------------------------------------------------- size and spot count
# The three things to change. The spots are sized to fill the wall, so the defaults give the same
# 27 x 36 mm spot as the tip cup and its 25 x 34 mm stickers fit. Other sizes need other stickers.
STAND_W = 132.0        # overall width
STAND_H = 68.0         # overall height, base included
SPOT_COLUMNS = 4       # per side
SPOT_ROWS = 1          # per side

# ---------------------------------------------------------------- sticker spots
SPOT_ASPECT = 4 / 3    # height / width: 4/3 is a phone photo held upright, 16/9 a screenshot
SPOT_DEPTH = 1.5
SPOT_CORNER_R = 4.0
SPOT_GAP = 4.0         # minimum space between neighbouring spots
SPOT_MARGIN = 6.0      # space kept clear at the sides and top of the block of spots
SPOT_BOTTOM_MARGIN = 20.0  # minimum plain wall between the base and the bottom of the spots

# ---------------------------------------------------------------- stand
BASE_T = 6.0
BASE_D = 50.0          # front to back; the wall stands in the middle
BASE_CORNER_R = 8.0
WALL_T = 8.0           # spots are cut from both faces, so this leaves 5 mm between them
WALL_CORNER_R = 6.0    # top corners of the wall
ROOT_R = 3.0           # concave fillet where the wall meets the base, for strength
EDGE_CHAMFER = 0.6     # bottom edge, so first-layer squish doesn't leave a lip

OUT = Path(__file__).parent / "out"

# the area of the wall the spots can use, and the largest spot that fits it
AREA_W = STAND_W - 2 * SPOT_MARGIN
AREA_H = STAND_H - BASE_T - SPOT_BOTTOM_MARGIN - SPOT_MARGIN
SPOT_W = min((AREA_W - (SPOT_COLUMNS - 1) * SPOT_GAP) / SPOT_COLUMNS,
             (AREA_H - (SPOT_ROWS - 1) * SPOT_GAP) / SPOT_ROWS / SPOT_ASPECT)
SPOT_H = SPOT_W * SPOT_ASPECT


def spread(count, spot, start, length):
    """Centres of spots spread evenly along a line, with the outer two at its ends."""
    if count == 1:
        return [start + length / 2]
    return [start + spot / 2 + i * (length - spot) / (count - 1) for i in range(count)]


def spot_centres():
    """(x, z) of each spot; the back of the wall mirrors the front."""
    xs = spread(SPOT_COLUMNS, SPOT_W, -AREA_W / 2, AREA_W)
    zs = spread(SPOT_ROWS, SPOT_H, BASE_T + SPOT_BOTTOM_MARGIN, AREA_H)
    return [(x, z) for z in zs for x in xs]


def build_stand():
    if SPOT_W <= 2 * SPOT_CORNER_R:
        raise ValueError(f"{STAND_W:g} x {STAND_H:g} mm is too small for {SPOT_COLUMNS} x {SPOT_ROWS} "
                         f"spots: they would be {SPOT_W:.1f} mm wide")

    base = extrude(RectangleRounded(STAND_W, BASE_D, BASE_CORNER_R), amount=BASE_T)

    wall = extrude(Plane.XZ * Pos(0, STAND_H / 2) * Rectangle(STAND_W, STAND_H),
                   amount=WALL_T / 2, both=True)
    top_corners = wall.edges().filter_by(Axis.Y).sort_by(Axis.Z)[-2:]
    wall = fillet(top_corners, WALL_CORNER_R)

    stand = base + wall
    root_edges = [e for e in stand.edges().filter_by(Axis.X)
                  if abs(e.center().Z - BASE_T) < 1e-6 and abs(abs(e.center().Y) - WALL_T / 2) < 1e-6]
    stand = fillet(root_edges, ROOT_R)
    stand = chamfer(stand.faces().sort_by(Axis.Z)[0].edges(), EDGE_CHAMFER)

    # both planes face -Y, so the front cuts backwards into the wall and the back cuts forwards
    for face, depth in ((Plane.XZ.offset(WALL_T / 2), -SPOT_DEPTH),
                        (Plane.XZ.offset(-WALL_T / 2), SPOT_DEPTH)):
        for x, z in spot_centres():
            stand -= extrude(face * Pos(x, z) * RectangleRounded(SPOT_W, SPOT_H, SPOT_CORNER_R),
                             amount=depth)
    return stand


def main():
    OUT.mkdir(exist_ok=True)
    print(f"spots: {SPOT_COLUMNS} x {SPOT_ROWS} per side at {SPOT_W:.1f} x {SPOT_H:.1f} mm "
          f"-> {SPOT_W - 2:.1f} x {SPOT_H - 2:.1f} mm stickers")
    print("building stand...")
    stand = build_stand()
    box = stand.bounding_box()
    print(f"  stand: valid={stand.is_valid}, volume={stand.volume / 1000:.1f} cm^3, "
          f"size={box.size.X:.1f} x {box.size.Y:.1f} x {box.size.Z:.1f} mm")

    export_stl(stand, OUT / "stand.stl", tolerance=0.01, angular_tolerance=0.1)
    export_step(stand, OUT / "sticker_stand.step")
    sticker = {"name": "spot", "width": SPOT_W - 2, "height": SPOT_H - 2,
               "corner": SPOT_CORNER_R - 1, "count": 2 * SPOT_COLUMNS * SPOT_ROWS}
    (OUT / "stickers.json").write_text(json.dumps([sticker], indent=2) + "\n", encoding="utf-8")
    print("done ->", OUT)


if __name__ == "__main__":
    main()
