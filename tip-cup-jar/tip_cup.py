"""Coffee-cup tip jar: threaded cup and a screw-on lid with a money slot.

All dimensions are in millimetres. Change the parameters below and re-run from the repo root:

    .venv/Scripts/python tip-cup-jar/tip_cup.py

Outputs go to tip-cup-jar/out:
    cup.stl     - print upright, no supports
    lid.stl     - already flipped top-down for printing, no supports
    tip_cup_assembly.step - cup and lid assembled, for viewing/editing in other CAD tools
    stickers.json - sticker sizes for the configurator's sticker editor
"""

import json
from math import cos, floor, pi, sin, radians, sqrt
from pathlib import Path

from build123d import (
    Axis, Compound, Plane, Polyline, Pos, RectangleRounded, Rot, SlotOverall, Solid, Vector,
    export_step, export_stl, extrude, make_face, revolve,
)
from bd_warehouse.thread import Thread

# ---------------------------------------------------------------- cup body
CUP_H = 86.0           # height of the tapered body (shoulder sits at the top of it)
CUP_R_BOTTOM = 38.8    # outer radius at the base
CUP_R_TOP = 44.0       # outer radius at the shoulder
CUP_WALL = 3.2
CUP_FLOOR = 3.0

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
# Portrait spots shaped like a phone photo. Each spot is sized automatically to the largest
# whole-millimetre size that fits the counts below, so more spots means smaller spots.
STICKER_DEPTH = 1.5
SPOT_ASPECT = 4 / 3      # height / width: 4/3 is a phone photo held upright, 16/9 a screenshot
SPOT_CORNER_R = 4.0
SPOT_GAP = 4.0           # minimum space between neighbouring spots
SPOT_START_ANGLE = 45    # angle of the first column; the front of the cup faces -Y (270 deg)
CUP_SPOT_COLUMNS = 4     # spots around the cup
CUP_SPOT_ROWS = 2
CUP_SPOT_MARGIN = 5.0    # space kept clear at the base and below the shoulder
LID_SPOTS = 4            # spots around the lid; lined up with the cup's columns when equal
LID_SPOT_MARGIN = 3.0    # space kept clear at the bottom and top of the lid's sloped face
SAME_SPOT_SIZE = False   # True shrinks the larger spots to match, so every sticker is one size

# ---------------------------------------------------------------- lid
LID_LIP_R = 47.5       # outer radius of the rim band
LID_LIP_H = 14.0
LID_FRUSTUM_Z0 = 17.0  # frustum starts here (45 deg chamfer from the lip up to it)
LID_FRUSTUM_R0 = 44.5
LID_TOP_Z = 57.0
LID_TOP_R = 33.0
LID_WALL = 3.2
LID_TOP_CHAMFER = 2.0
SLOT_L, SLOT_W = 50.0, 10.0  # wide enough that folded bills and coins drop in easily

OUT = Path(__file__).parent / "out"


def cup_r(z):
    """Outer radius of the tapered cup body at height z."""
    return CUP_R_BOTTOM + (CUP_R_TOP - CUP_R_BOTTOM) * z / CUP_H


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


def cup_spot_band():
    """Lowest and highest z the cup's spots may reach."""
    return CUP_SPOT_MARGIN, CUP_H - CUP_SPOT_MARGIN


def lid_spot_band():
    """Lowest and highest lid z the lid's spots may reach."""
    return LID_FRUSTUM_Z0 + LID_SPOT_MARGIN, LID_TOP_Z - LID_TOP_CHAMFER - LID_SPOT_MARGIN


def spot_angles(count):
    return [SPOT_START_ANGLE + 360 * i / count for i in range(count)]


def fit_spot_width(count, r, height):
    """Widest portrait spot, in whole mm, that fits count around radius r and within height.

    The flat spot is projected straight onto the surface, so its angular span is 2*asin(w/2r);
    past 60 degrees either side the projection smears too much to be worth it.
    """
    half_angle = min(pi / count - SPOT_GAP / (2 * r), pi / 3)
    return floor(min(2 * r * sin(half_angle), height / SPOT_ASPECT))


def spot_sizes():
    """{"cup": (w, h), "lid": (w, h)} for each part that has spots."""
    widths = {}
    if CUP_SPOT_COLUMNS and CUP_SPOT_ROWS:
        lo, hi = cup_spot_band()
        row_h = (hi - lo - (CUP_SPOT_ROWS - 1) * SPOT_GAP) / CUP_SPOT_ROWS
        widths["cup"] = fit_spot_width(CUP_SPOT_COLUMNS, cup_r(lo), row_h)
    if LID_SPOTS:
        lo, hi = lid_spot_band()
        widths["lid"] = fit_spot_width(LID_SPOTS, lid_r(hi), hi - lo)  # narrowest at the top
    if SAME_SPOT_SIZE and widths:
        widths = dict.fromkeys(widths, min(widths.values()))

    sizes = {}
    for part, w in widths.items():
        if w < 2 * SPOT_CORNER_R + 2:
            raise ValueError(f"{part} spots would only be {w} mm wide; "
                             "use fewer spots, a smaller SPOT_GAP or smaller margins")
        sizes[part] = (w, floor(w * SPOT_ASPECT + 1e-9))
    return sizes


def stickers():
    """Each sticker's size. They're 1 mm smaller all round than their recess, for Cricut's cutting."""
    counts = {"cup": CUP_SPOT_COLUMNS * CUP_SPOT_ROWS, "lid": LID_SPOTS}
    return [{"name": part, "width": w - 2, "height": h - 2, "corner": SPOT_CORNER_R - 1,
             "count": counts[part]} for part, (w, h) in spot_sizes().items()]


def multi_start_thread(**kwargs):
    lead = THREAD_PITCH * THREAD_STARTS
    starts = [Thread(pitch=lead, **kwargs) for _ in range(THREAD_STARTS)]
    return [Rot(0, 0, 360 * i / THREAD_STARTS) * t for i, t in enumerate(starts)]


# ------------------------------------------------------------------- cup
def build_cup():
    w, fl = CUP_WALL, CUP_FLOOR
    top = CUP_H + NECK_H
    # inner wall follows the outer taper, then steps in to the neck at 45 deg
    z_step = CUP_H - ((cup_r(CUP_H) - w) - (NECK_R - NECK_WALL))
    r_neck_in = NECK_R - NECK_WALL
    pts = [
        (0, 0), (CUP_R_BOTTOM - 1.0, 0), (cup_r(1.0), 1.0),          # base chamfer
        (cup_r(CUP_H), CUP_H), (NECK_R, CUP_H),                       # shoulder
        (NECK_R, top - 0.8), (NECK_R - 0.8, top),                     # neck top chamfer
        (r_neck_in, top), (r_neck_in, CUP_H),
        (cup_r(z_step) - w, z_step),
        (cup_r(fl) - w, fl), (0, fl),
    ]
    cup = revolve_profile(pts)

    thread_len = NECK_H - 3.2
    threads = multi_start_thread(
        apex_radius=NECK_R + THREAD_DEPTH, apex_width=EXT_APEX_W,
        root_radius=NECK_R, root_width=EXT_ROOT_W,
        length=thread_len, end_finishes=("fade", "fade"),
    )
    for t in threads:
        cup += Pos(0, 0, CUP_H + 1.8) * t

    size = spot_sizes().get("cup")
    if size is None:
        return cup
    w, h = size
    # rows are packed SPOT_GAP apart and centred in the band
    lo, hi = cup_spot_band()
    block_h = CUP_SPOT_ROWS * h + (CUP_SPOT_ROWS - 1) * SPOT_GAP
    z_first = (lo + hi - block_h) / 2 + h / 2
    shell = cone_shell(CUP_R_BOTTOM, CUP_R_TOP, 0, CUP_H, STICKER_DEPTH, 5)
    spot = lambda: RectangleRounded(w, h, SPOT_CORNER_R)
    for row in range(CUP_SPOT_ROWS):
        zc = z_first + row * (h + SPOT_GAP)
        for ang in spot_angles(CUP_SPOT_COLUMNS):
            cup -= radial_prism(spot, ang, zc, CUP_R_TOP + 10) & shell
    return cup


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

    size = spot_sizes().get("lid")
    if size is None:
        return lid
    w, h = size
    shell = cone_shell(LID_FRUSTUM_R0, LID_TOP_R, LID_FRUSTUM_Z0, LID_TOP_Z,
                       STICKER_DEPTH * sqrt(1 + slope**2), 5)
    spot = lambda: RectangleRounded(w, h, SPOT_CORNER_R)
    zc = sum(lid_spot_band()) / 2
    for ang in spot_angles(LID_SPOTS):
        lid -= radial_prism(spot, ang, zc, LID_LIP_R + 10) & shell
    return lid


def main():
    OUT.mkdir(exist_ok=True)
    counts = {"cup": f"{CUP_SPOT_COLUMNS} x {CUP_SPOT_ROWS}", "lid": f"{LID_SPOTS}"}
    for part, (w, h) in spot_sizes().items():
        # stickers are 1 mm smaller all round so Cricut's cut tolerance stays inside the recess
        print(f"{part} spots: {counts[part]} at {w} x {h} mm -> {w - 2} x {h - 2} mm stickers")
    print("building cup...")
    cup = build_cup()
    print("building lid...")
    lid = build_lid()

    for name, part in (("cup", cup), ("lid", lid)):
        print(f"  {name}: valid={part.is_valid}, volume={part.volume / 1000:.1f} cm^3")

    lid_print = Rot(180, 0, 0) * lid
    lid_print = Pos(0, 0, -lid_print.bounding_box().min.Z) * lid_print
    export_stl(cup, OUT / "cup.stl", tolerance=0.01, angular_tolerance=0.1)
    export_stl(lid_print, OUT / "lid.stl", tolerance=0.01, angular_tolerance=0.1)

    assembly = Compound(children=[cup, Pos(0, 0, CUP_H) * lid])
    export_step(assembly, OUT / "tip_cup_assembly.step")
    (OUT / "stickers.json").write_text(json.dumps(stickers(), indent=2) + "\n", encoding="utf-8")
    print("done ->", OUT)


if __name__ == "__main__":
    main()
