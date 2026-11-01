"""Coffee-cup tip jar: threaded cup, screw-on lid with money slot, and a slide-on sleeve.

All dimensions are in millimetres. Change the parameters below and re-run from the repo root:

    .venv/Scripts/python tip-cup-jar/tip_cup.py

Outputs go to tip-cup-jar/out:
    cup.stl     - print upright, no supports
    lid.stl     - already flipped top-down for printing, no supports (fits both cups)
    sleeve.stl  - print upright, no supports (slides on from the bottom of the cup)
    cup_short.stl - shorter cup without a sleeve, same 8 sticker spots
    tip_cup_assembly.step / tip_cup_short_assembly.step - assembled, for other CAD tools
"""

from math import cos, sin, radians, sqrt
from pathlib import Path

from build123d import (
    Axis, Circle, Compound, FontStyle, Location, Plane, Polyline, Pos, Rectangle,
    RectangleRounded, Rot, SlotOverall, Solid, Text, Vector, export_step, export_stl,
    extrude, make_face, revolve,
)
from bd_warehouse.thread import Thread

# ---------------------------------------------------------------- cup body
CUP_H = 150.0          # height of the tapered body (shoulder sits at the top of it)
CUP_R_BOTTOM = 35.0    # outer radius at the base
CUP_R_TOP = 44.0       # outer radius at the shoulder
CUP_WALL = 3.2
CUP_FLOOR = 3.0

# ---------------------------------------------------------------- short cup (no sleeve)
SHORT_CUP_H = 86.0
SHORT_CUP_R_BOTTOM = 38.8                  # keeps the same taper as the tall cup
SHORT_CUP_SPOT_ROWS_Z = (24.0, 61.0)

# ---------------------------------------------------------------- threaded neck
NECK_H = 16.0          # neck height above the shoulder
NECK_R = 40.0          # neck outer radius = thread root radius
NECK_WALL = 2.4
THREAD_DEPTH = 1.5
THREAD_STARTS = 2      # 2-start thread: lid goes on/off in about one turn
THREAD_PITCH = 5.0     # axial distance between neighbouring teeth
THREAD_CLEARANCE = 0.4 # radial gap between mating crests and roots
THREAD_AXIAL_GAP = 0.35  # per-flank axial play (clearance normal to flank = gap * 0.71)
# 45 degree flanks so the threads print without support in either orientation
EXT_APEX_W = 0.6
EXT_ROOT_W = EXT_APEX_W + 2 * THREAD_DEPTH

# ---------------------------------------------------------------- sticker spots
STICKER_DEPTH = 1.5
CUP_SPOT_W, CUP_SPOT_H, SPOT_CORNER_R = 40.0, 30.0, 4.0
CUP_SPOT_ROWS_Z = (27.0, 129.0)            # centre heights of the two rows
CUP_SPOT_ANGLES = (45, 135, 225, 315)      # front of the cup faces -Y (270 deg)
LID_SPOT_W, LID_SPOT_H = CUP_SPOT_W, CUP_SPOT_H  # one sticker size for everything
LID_SPOT_ANGLES = CUP_SPOT_ANGLES                 # lined up with the cup's columns

# ---------------------------------------------------------------- sleeve
SLEEVE_Z0, SLEEVE_Z1 = 50.0, 106.0
SLEEVE_THICK = 2.4
SLEEVE_CLEARANCE = 0.15  # radial; the taper makes it wedge tight as it slides up
SLEEVE_TEXT = ("Tips", "Make", "Better", "Days")  # set to () for a plain sleeve
SLEEVE_FONT = "Georgia"
SLEEVE_FONT_SIZE = 10.0
SLEEVE_LINE_PITCH = 10.2
SLEEVE_HEART = True
EMBOSS = 0.8

# ---------------------------------------------------------------- lid
LID_LIP_R = 47.5       # outer radius of the rim band
LID_LIP_H = 14.0
LID_FRUSTUM_Z0 = 17.0  # frustum starts here (45 deg chamfer from the lip up to it)
LID_FRUSTUM_R0 = 44.5
LID_TOP_Z = 57.0
LID_TOP_R = 33.0
LID_WALL = 3.2
LID_TOP_CHAMFER = 2.0
SLOT_L, SLOT_W = 50.0, 5.0

OUT = Path(__file__).parent / "out"


def cup_r(z, height=CUP_H, r_bottom=CUP_R_BOTTOM):
    """Outer radius of the tapered cup body at height z."""
    return r_bottom + (CUP_R_TOP - r_bottom) * z / height


def lid_r(z):
    """Outer radius of the lid frustum at lid height z."""
    t = (z - LID_FRUSTUM_Z0) / (LID_TOP_Z - LID_FRUSTUM_Z0)
    return LID_FRUSTUM_R0 + (LID_TOP_R - LID_FRUSTUM_R0) * t


def revolve_profile(pts):
    """Revolve a closed (r, z) polyline around the Z axis."""
    face = make_face(Polyline(*[Vector(r, 0, z) for r, z in pts], close=True))
    return revolve(face, axis=Axis.Z)


def radial_prism(sketch_fn, angle_deg, zc, reach):
    """Extrude a flat sketch outward from the Z axis toward angle_deg.

    Intersecting the result with a thin shell projects the sketch onto a curved surface.
    """
    a = radians(angle_deg)
    plane = Plane(origin=(0, 0, zc), x_dir=(-sin(a), cos(a), 0), z_dir=(cos(a), sin(a), 0))
    return extrude(plane * sketch_fn(), amount=reach)


def cone_shell(r0, r1, z0, z1, inner_off, outer_off):
    """Solid between two cones offset radially from the cone r0@z0 -> r1@z1."""
    h = z1 - z0
    outer = Solid.make_cone(r0 + outer_off, r1 + outer_off, h, Plane.XY.offset(z0))
    inner = Solid.make_cone(r0 - inner_off, r1 - inner_off, h, Plane.XY.offset(z0))
    return outer - inner


def multi_start_thread(**kwargs):
    lead = THREAD_PITCH * THREAD_STARTS
    starts = [Thread(pitch=lead, **kwargs) for _ in range(THREAD_STARTS)]
    return [Rot(0, 0, 360 * i / THREAD_STARTS) * t for i, t in enumerate(starts)]


# ------------------------------------------------------------------- cup
def build_cup(height=CUP_H, r_bottom=CUP_R_BOTTOM, spot_rows_z=CUP_SPOT_ROWS_Z):
    w, fl = CUP_WALL, CUP_FLOOR
    top = height + NECK_H
    r = lambda z: cup_r(z, height, r_bottom)
    # inner wall follows the outer taper, then steps in to the neck at 45 deg
    z_step = height - ((r(height) - w) - (NECK_R - NECK_WALL))
    r_neck_in = NECK_R - NECK_WALL
    pts = [
        (0, 0), (r_bottom - 1.0, 0), (r(1.0), 1.0),                   # base chamfer
        (r(height), height), (NECK_R, height),                        # shoulder
        (NECK_R, top - 0.8), (NECK_R - 0.8, top),                     # neck top chamfer
        (r_neck_in, top), (r_neck_in, height),
        (r(z_step) - w, z_step),
        (r(fl) - w, fl), (0, fl),
    ]
    cup = revolve_profile(pts)

    thread_len = NECK_H - 3.2
    threads = multi_start_thread(
        apex_radius=NECK_R + THREAD_DEPTH, apex_width=EXT_APEX_W,
        root_radius=NECK_R, root_width=EXT_ROOT_W,
        length=thread_len, end_finishes=("fade", "fade"),
    )
    for t in threads:
        cup += Pos(0, 0, height + 1.8) * t

    shell = cone_shell(r_bottom, CUP_R_TOP, 0, height, STICKER_DEPTH, 5)
    spot = lambda: RectangleRounded(CUP_SPOT_W, CUP_SPOT_H, SPOT_CORNER_R)
    for zc in spot_rows_z:
        for ang in CUP_SPOT_ANGLES:
            cup -= radial_prism(spot, ang, zc, CUP_R_TOP + 10) & shell
    return cup


# ------------------------------------------------------------------- sleeve
def heart(size):
    """Heart shape centred roughly on the origin, about 1.55 * size tall."""
    h = size / (2 * sqrt(2))
    body = Rot(0, 0, 45) * Rectangle(size, size)
    return body + Pos(-h, h) * Circle(size / 2) + Pos(h, h) * Circle(size / 2)


def sleeve_label():
    lines = list(SLEEVE_TEXT)
    n = len(lines) + (1 if SLEEVE_HEART else 0)
    heart_size = SLEEVE_FONT_SIZE * 0.45
    # stack lines top to bottom, centred on the sketch origin
    y = (n - 1) * SLEEVE_LINE_PITCH / 2
    sk = None
    for line in lines:
        txt = Pos(0, y) * Text(line, SLEEVE_FONT_SIZE, font=SLEEVE_FONT,
                               font_style=FontStyle.BOLD)
        sk = txt if sk is None else sk + txt
        y -= SLEEVE_LINE_PITCH
    if SLEEVE_HEART:
        hrt = Pos(0, y - SLEEVE_LINE_PITCH * 0.15) * heart(heart_size)  # clear descenders
        sk = hrt if sk is None else sk + hrt
    return Pos(0, -sk.bounding_box().center().Y) * sk


def build_sleeve():
    c, t = SLEEVE_CLEARANCE, SLEEVE_THICK
    z0, z1, ch = SLEEVE_Z0, SLEEVE_Z1, 0.6
    ri0, ri1 = cup_r(z0) + c, cup_r(z1) + c
    pts = [
        (ri0, z0), (ri0 + t - ch, z0), (ri0 + t, z0 + ch),
        (ri1 + t, z1 - ch), (ri1 + t - ch, z1), (ri1, z1),
    ]
    sleeve = revolve_profile(pts)
    if SLEEVE_TEXT or SLEEVE_HEART:
        shell = cone_shell(ri0 + t, ri1 + t, z0, z1, 0.3, EMBOSS)
        sleeve += radial_prism(sleeve_label, 270, (z0 + z1) / 2, CUP_R_TOP + 10) & shell
    return sleeve


# ------------------------------------------------------------------- lid
def build_lid():
    """Lid in assembled orientation; z=0 is the face that seats on the cup shoulder."""
    r_skirt = NECK_R + THREAD_DEPTH + THREAD_CLEARANCE   # internal thread root
    skirt_top = NECK_H + 1.0
    # inner frustum offset by the wall thickness measured normal to the slope
    slope = (LID_FRUSTUM_R0 - LID_TOP_R) / (LID_TOP_Z - LID_FRUSTUM_Z0)
    off = LID_WALL * sqrt(1 + slope**2)
    z_ceiling = LID_TOP_Z - LID_WALL
    pts = [
        (r_skirt + 0.7, 0), (LID_LIP_R - 0.6, 0), (LID_LIP_R, 0.6),
        (LID_LIP_R, LID_LIP_H), (LID_FRUSTUM_R0, LID_FRUSTUM_Z0),
        (lid_r(LID_TOP_Z - LID_TOP_CHAMFER), LID_TOP_Z - LID_TOP_CHAMFER),
        (LID_TOP_R - LID_TOP_CHAMFER, LID_TOP_Z), (0, LID_TOP_Z),
        (0, z_ceiling), (lid_r(z_ceiling) - off, z_ceiling),
        (lid_r(skirt_top) - off, skirt_top), (r_skirt, skirt_top),
        (r_skirt, 0.7),                                               # lead-in chamfer
    ]
    lid = revolve_profile(pts)

    # with 45 deg flanks the two tooth widths at any shared radius sum to
    # EXT_APEX_W + int_apex + 2 * (radial overlap); size int_apex so that sum leaves
    # THREAD_AXIAL_GAP of play on each flank
    overlap = THREAD_DEPTH - THREAD_CLEARANCE
    int_apex = THREAD_PITCH - 2 * THREAD_AXIAL_GAP - EXT_APEX_W - 2 * overlap
    threads = multi_start_thread(
        apex_radius=NECK_R + THREAD_CLEARANCE, apex_width=int_apex,
        root_radius=r_skirt, root_width=int_apex + 2 * THREAD_DEPTH,
        length=skirt_top - 1.5, end_finishes=("fade", "fade"),
    )
    for t in threads:
        lid += Pos(0, 0, 0.5) * t

    lid -= Pos(0, 0, LID_TOP_Z) * extrude(SlotOverall(SLOT_L, SLOT_W), amount=10, both=True)

    shell = cone_shell(LID_FRUSTUM_R0, LID_TOP_R, LID_FRUSTUM_Z0, LID_TOP_Z,
                       STICKER_DEPTH * sqrt(1 + slope**2), 5)
    spot = lambda: RectangleRounded(LID_SPOT_W, LID_SPOT_H, SPOT_CORNER_R)
    zc = (LID_FRUSTUM_Z0 + LID_TOP_Z - LID_TOP_CHAMFER) / 2
    for ang in LID_SPOT_ANGLES:
        lid -= radial_prism(spot, ang, zc, LID_LIP_R + 10) & shell
    return lid


def main():
    OUT.mkdir(exist_ok=True)
    print("building cup...")
    cup = build_cup()
    print("building sleeve...")
    sleeve = build_sleeve()
    print("building lid...")
    lid = build_lid()
    print("building short cup...")
    cup_short = build_cup(SHORT_CUP_H, SHORT_CUP_R_BOTTOM, SHORT_CUP_SPOT_ROWS_Z)

    for name, part in (("cup", cup), ("sleeve", sleeve), ("lid", lid),
                       ("cup_short", cup_short)):
        print(f"  {name}: valid={part.is_valid}, volume={part.volume / 1000:.1f} cm^3")

    lid_print = Rot(180, 0, 0) * lid
    lid_print = Pos(0, 0, -lid_print.bounding_box().min.Z) * lid_print
    export_stl(cup, OUT / "cup.stl", tolerance=0.01, angular_tolerance=0.1)
    export_stl(sleeve, OUT / "sleeve.stl", tolerance=0.01, angular_tolerance=0.1)
    export_stl(lid_print, OUT / "lid.stl", tolerance=0.01, angular_tolerance=0.1)
    export_stl(cup_short, OUT / "cup_short.stl", tolerance=0.01, angular_tolerance=0.1)

    assembly = Compound(children=[cup, sleeve, Pos(0, 0, CUP_H) * lid])
    export_step(assembly, OUT / "tip_cup_assembly.step")
    short_assembly = Compound(children=[cup_short, Pos(0, 0, SHORT_CUP_H) * lid])
    export_step(short_assembly, OUT / "tip_cup_short_assembly.step")
    print("done ->", OUT)


if __name__ == "__main__":
    main()
