"""Sticker stand: a desktop stand shaped like an upside-down T, with a flat base and a vertical
wall that has recessed sticker spots on both its front and back.

All dimensions are in millimetres. Change the parameters below and re-run from the repo root:

    .venv/Scripts/python sticker-stand/sticker_stand.py

Outputs go to sticker-stand/out:
    stand.stl           - print flat on its base, no supports
    sticker_stand.step  - the stand, for viewing/editing in other CAD tools

Axes: X runs left to right, Y from front to back, Z up.
"""

from pathlib import Path

from build123d import (
    Axis, Plane, Pos, Rectangle, RectangleRounded, chamfer, export_step, export_stl, extrude,
    fillet,
)

# ---------------------------------------------------------------- sticker spots
# The default spot matches the tip cup's, so the same 25 x 34 mm stickers fit both. The wall is
# sized around the spots, so changing anything here resizes the stand.
SPOT_W, SPOT_H = 27.0, 36.0
SPOT_COLUMNS = 4       # per side
SPOT_ROWS = 1          # per side
SPOT_DEPTH = 1.5
SPOT_CORNER_R = 4.0
SPOT_GAP = 4.0         # space between neighbouring spots
SPOT_MARGIN = 6.0      # space kept clear at the sides and top of the block of spots
SPOT_BOTTOM_MARGIN = 20.0  # plain wall between the base and the bottom of the spots

# ---------------------------------------------------------------- stand
BASE_T = 6.0
BASE_D = 50.0          # front to back; the wall stands in the middle
BASE_CORNER_R = 8.0
WALL_T = 8.0           # spots are cut from both faces, so this leaves 5 mm between them
WALL_CORNER_R = 6.0    # top corners of the wall
ROOT_R = 3.0           # concave fillet where the wall meets the base, for strength
EDGE_CHAMFER = 0.6     # bottom edge, so first-layer squish doesn't leave a lip

OUT = Path(__file__).parent / "out"

BLOCK_W = SPOT_COLUMNS * SPOT_W + (SPOT_COLUMNS - 1) * SPOT_GAP
BLOCK_H = SPOT_ROWS * SPOT_H + (SPOT_ROWS - 1) * SPOT_GAP
STAND_W = BLOCK_W + 2 * SPOT_MARGIN
STAND_H = BASE_T + SPOT_BOTTOM_MARGIN + BLOCK_H + SPOT_MARGIN


def spot_centres():
    """(x, z) of each spot; the back of the wall mirrors the front."""
    x0 = (SPOT_W - BLOCK_W) / 2
    z0 = BASE_T + SPOT_BOTTOM_MARGIN + SPOT_H / 2
    return [(x0 + col * (SPOT_W + SPOT_GAP), z0 + row * (SPOT_H + SPOT_GAP))
            for row in range(SPOT_ROWS) for col in range(SPOT_COLUMNS)]


def build_stand():
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
    print(f"spots: {SPOT_COLUMNS} x {SPOT_ROWS} per side at {SPOT_W:g} x {SPOT_H:g} mm "
          f"-> {SPOT_W - 2:g} x {SPOT_H - 2:g} mm stickers")
    print("building stand...")
    stand = build_stand()
    box = stand.bounding_box()
    print(f"  stand: valid={stand.is_valid}, volume={stand.volume / 1000:.1f} cm^3, "
          f"size={box.size.X:.1f} x {box.size.Y:.1f} x {box.size.Z:.1f} mm")

    export_stl(stand, OUT / "stand.stl", tolerance=0.01, angular_tolerance=0.1)
    export_step(stand, OUT / "sticker_stand.step")
    print("done ->", OUT)


if __name__ == "__main__":
    main()
