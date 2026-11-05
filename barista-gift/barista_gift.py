"""Birthday tip cup for a barista: the tip cup jar with a raised name, "Happy Birthday" and two
QR code billboards for payment apps.

The thread, lid and coin slot come from tip-cup-jar/tip_cup.py, so fit changes made there carry
over. All dimensions are in millimetres. Run from the repo root:

    .venv/Scripts/python barista-gift/barista_gift.py --name "Jamie"

Outputs go to barista-gift/out:
    cup.stl     - print upright, no supports
    lid.stl     - already flipped top-down for printing, no supports
    barista_gift_assembly.step - cup and lid assembled, for viewing/editing in other CAD tools
    stickers.json - sticker sizes for the configurator's sticker editor
"""

import argparse
import json
import sys
from math import degrees, sqrt
from pathlib import Path

from build123d import (
    CenterArc, CenterOf, Compound, FontStyle, Line, Plane, Polyline, Pos, RectangleRounded,
    Rot, Solid, Text, export_step, export_stl, extrude, make_face, mirror,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tip-cup-jar"))
import tip_cup as base  # noqa: E402

# ---------------------------------------------------------------- front text
# NAME, FONT, NAME_SIZE, GREETING and GREETING_SIZE are defaults for the command-line options
NAME = "Jamie"
FONT = "Arial"           # any installed font, e.g. "Segoe Script" for handwriting
FRONT_ANGLE = 270        # the front of the cup faces -Y
TEXT_RELIEF = 1.2        # how far the letters stand out from the cup
NAME_SIZE = 20.0         # font size in mm; text wider than its MAX_W shrinks to fit
NAME_MAX_W = 64.0        # measured around the cup
NAME_Z = 38.0            # centre height of the name
GREETING = "Happy Birthday"
GREETING_SIZE = 8.0
GREETING_MAX_W = 70.0
GREETING_Z = 64.0

# ---------------------------------------------------------------- QR billboards
# One on each side of the cup (+X and -X), facing the front like the name. Each sits on a post
# that runs out along the table from the base of the cup and curves up like a mug handle.
# The panel's V-shaped bottom and the 45 degree chamfer under the curve let it all print
# upright without supports.
BB_W, BB_H, BB_T = 44.0, 44.0, 4.0  # panel width, height (above the V) and thickness
BB_GAP = 3.0             # space between the cup's widest point and the panel's inner edge
BB_TOP = base.CUP_H - 2  # top of the panel, just below the lid
POST_W = 7.0             # post thickness seen from the front
POST_D = 8.0             # post thickness seen from the side
POST_BEND_R = 17.0       # radius of the curve, measured to the middle of the post
QR_RECESS, QR_CORNER_R, QR_DEPTH = 38.0, 2.0, 1.0  # takes a 36 mm square QR sticker

# ---------------------------------------------------------------- photo spots
# The name is on the front and the billboards are on the sides, so the cup's photo spots
# go in one column on the back. The lid keeps its spots.
base.CUP_SPOT_COLUMNS = 1
base.SPOT_START_ANGLE = 90

# ---------------------------------------------------------------- lid
base.SLOT_W = 10.0       # wide enough that folded bills and coins drop in easily

OUT = Path(__file__).parent / "out"


def raised_text(txt, font, size, max_w, zc):
    """Letters standing TEXT_RELIEF proud of the cup, centred on the front at height zc.

    Each glyph is projected at its own angle around the cup, so a long line wraps around the
    curve instead of smearing at the ends.
    """
    sketch = Text(txt, size, font=font, font_style=FontStyle.BOLD)
    w = sketch.bounding_box().size.X
    if w > max_w:
        print(f"  {txt!r} is {w:.0f} mm wide at size {size:g}; shrinking to fit {max_w:g} mm")
        sketch = Text(txt, size * max_w / w, font=font, font_style=FontStyle.BOLD)
    r = base.cup_r(zc)
    shell = base.cone_shell(base.CUP_R_BOTTOM, base.CUP_R_TOP, 0, base.CUP_H, 0.3, TEXT_RELIEF)
    letters = []
    for face in sketch.faces():
        cx = face.center(CenterOf.BOUNDING_BOX).X
        glyph = lambda f=face, cx=cx: Pos(-cx, 0) * f
        prism = base.radial_prism(glyph, FRONT_ANGLE + degrees(cx / r), zc, base.CUP_R_TOP + 10)
        letters.append(prism & shell)
    return letters


def billboard():
    """QR billboard and its handle-shaped post on the +X side of the cup.

    Drawn in the XZ plane (sketch y is height) and extruded through Y.
    """
    x_post = base.CUP_R_TOP + BB_GAP + BB_W / 2   # middle of the post and panel
    z_bottom = BB_TOP - BB_H                       # bottom of the panel's square part
    z_apex = z_bottom - (BB_W - POST_W) / 2        # tip of the V, where the post joins

    # post: along the table from inside the cup wall, then a quarter turn up to vertical
    cx, r_out, r_in = x_post - POST_BEND_R, POST_BEND_R + POST_W / 2, POST_BEND_R - POST_W / 2
    cz = r_out                                     # outer curve just touches the table
    if z_apex < cz:
        raise ValueError("the post's curve reaches past the bottom of the panel; "
                         "use a smaller POST_BEND_R or a shorter panel")
    k = r_out * sqrt(0.5)
    x_foot = cx + 2 * k - r_out                    # where the chamfer under the curve meets the table
    x_wall = base.cup_r(0) - 4                     # starts inside the wall; cavity trimmed below
    post = make_face(
        Line((x_wall, 0), (x_foot, 0))
        # 45 deg chamfer up to where the outer curve gets steep enough to print
        + Line((x_foot, 0), (cx + k, cz - k))
        + CenterArc((cx, cz), r_out, -45, 45)
        + Line((cx + r_out, cz), (cx + r_out, z_apex + 1))
        + Line((cx + r_out, z_apex + 1), (cx + r_in, z_apex + 1))
        + Line((cx + r_in, z_apex + 1), (cx + r_in, cz))
        + CenterArc((cx, cz), r_in, 0, -90)
        + Line((cx, cz - r_in), (x_wall, cz - r_in))
        + Line((x_wall, cz - r_in), (x_wall, 0))
    )
    w, fl = base.CUP_WALL, base.CUP_FLOOR
    cavity = Solid.make_cone(base.cup_r(fl) - w, base.cup_r(base.CUP_H) - w, base.CUP_H,
                             Plane.XY.offset(fl))
    post = extrude(Plane.XZ * post, amount=POST_D / 2, both=True) - cavity

    hw, pw = BB_W / 2, POST_W / 2
    panel = make_face(Polyline(
        (x_post - hw, BB_TOP), (x_post + hw, BB_TOP), (x_post + hw, z_bottom),
        (x_post + pw, z_apex), (x_post - pw, z_apex), (x_post - hw, z_bottom), close=True,
    ))
    panel = extrude(Plane.XZ * panel, amount=BB_T / 2, both=True)
    front = Plane(origin=(x_post, -BB_T / 2, z_bottom + BB_H / 2), x_dir=(1, 0, 0),
                  z_dir=(0, -1, 0))
    panel -= extrude(front * RectangleRounded(QR_RECESS, QR_RECESS, QR_CORNER_R),
                     amount=-QR_DEPTH)
    return post + panel


def build_cup(args):
    cup = base.build_cup()
    cup = cup.fuse(
        *raised_text(args.name, args.font, args.name_size, NAME_MAX_W, NAME_Z),
        *raised_text(args.greeting, args.font, args.greeting_size, GREETING_MAX_W, GREETING_Z),
    )
    right = billboard()
    return cup.fuse(right, mirror(right, Plane.YZ)).clean()


def main():
    parser = argparse.ArgumentParser(description="Build the barista birthday tip cup STLs.")
    parser.add_argument("--name", default=NAME, help=f"name on the front (default {NAME!r})")
    parser.add_argument("--name-size", type=float, default=NAME_SIZE,
                        help=f"name font size in mm (default {NAME_SIZE:g})")
    parser.add_argument("--greeting", default=GREETING,
                        help=f"line above the name (default {GREETING!r})")
    parser.add_argument("--greeting-size", type=float, default=GREETING_SIZE,
                        help=f"greeting font size in mm (default {GREETING_SIZE:g})")
    parser.add_argument("--font", default=FONT, help=f"installed font name (default {FONT!r})")
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    for part, (w, h) in base.spot_sizes().items():
        print(f"{part} photo spots: {w} x {h} mm -> {w - 2} x {h - 2} mm stickers")
    print(f"QR billboards: {QR_RECESS:g} mm recesses -> {QR_RECESS - 2:g} mm square stickers")
    print(f"building cup for {args.name!r}...")
    cup = build_cup(args)
    print("building lid...")
    lid = base.build_lid()

    for name, part in (("cup", cup), ("lid", lid)):
        print(f"  {name}: valid={part.is_valid}, volume={part.volume / 1000:.1f} cm^3")

    lid_print = Rot(180, 0, 0) * lid
    lid_print = Pos(0, 0, -lid_print.bounding_box().min.Z) * lid_print
    export_stl(cup, OUT / "cup.stl", tolerance=0.01, angular_tolerance=0.1)
    export_stl(lid_print, OUT / "lid.stl", tolerance=0.01, angular_tolerance=0.1)

    assembly = Compound(children=[cup, Pos(0, 0, base.CUP_H) * lid])
    export_step(assembly, OUT / "barista_gift_assembly.step")
    qr_sticker = {"name": "QR code", "width": QR_RECESS - 2, "height": QR_RECESS - 2,
                  "corner": QR_CORNER_R - 1, "count": 2}
    (OUT / "stickers.json").write_text(json.dumps(base.stickers() + [qr_sticker], indent=2) + "\n",
                                       encoding="utf-8")
    print("done ->", OUT)


if __name__ == "__main__":
    main()
