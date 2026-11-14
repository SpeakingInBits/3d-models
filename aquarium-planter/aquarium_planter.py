"""Aquarium planter for a framed tank: a round cup with a perforated floor for feeding or holding
fry, joined to a slotted basket for a houseplant's roots. It either drops into a tray that rests on
the frame's inner lip, or hangs from two clip-on hooks that sit on the lip and wrap over the frame.

All dimensions are in millimetres. Change the parameters below and re-run from the repo root:

    .venv/Scripts/python aquarium-planter/aquarium_planter.py

Outputs go to aquarium-planter/out, each laid out the way it prints (no slicer supports):
    planter.stl    - rim up
    hook.stl       - print 2, lying flat on its side
    tray_half.stl  - print 2 (the halves are the same part), top face down
    tray_key.stl   - print 3, they join the two tray halves
    aquarium_planter.step, tray_half.step - for viewing/editing in other CAD tools

Axes: X runs along the tank wall, Y points out through the tank wall, Z up. The planter is built
with its flat back at Y = 0 and its rim at Z = HEIGHT.
"""

from math import sqrt
from pathlib import Path

from build123d import (
    Axis, Circle, Polyline, Pos, RectangleRounded, Rot, Solid, Vector, export_step, export_stl,
    extrude, make_face, offset,
)

# ---------------------------------------------------------------- tank frame
LIP_DROP = 8.5         # how far the lip is below the top edge of the frame
LIP_W = 10.0           # how far the lip sticks into the tank from the frame's inner wall
FRAME_TOP_W = 13.3     # across the frame top, inner wall to outer face: 9/16 in less 1 mm to grip
OPENING = 287.0        # between the front and back lip edges
FRAME_CLEAR = 0.8      # room around the frame in the hooks

# ---------------------------------------------------------------- body
HEIGHT = 60.0          # bottom to rim
WALL = 2.0
FLOOR = 2.0
FLANGE_W = 4.0         # rim flange the planter hangs from in the tray; not on the basket's back
FLANGE_T = 2.0         # flange thickness at its edge; a 45 degree chamfer supports it underneath

# ---------------------------------------------------------------- feeding cup
CUP_D = 72.0           # outside diameter at the rim
CUP_BOTTOM_D = 64.0    # outside diameter at the bottom; the cup tapers in like a pot
CUP_HOLE_D = 1.5       # floor holes; smaller than fry and food pellets, big enough for water
CUP_HOLE_PITCH = 3.5

# ---------------------------------------------------------------- plant basket
BASKET_L = 110.0       # along the tank wall, from where it joins the cup
BASKET_W = 60.0        # out from the tank wall
BASKET_CORNER_R = 4.0
BASKET_OVERLAP = 16.0  # how far the basket's end reaches back into the cup's outline
SLOT_W = 3.0           # vertical water slots in the basket walls
SLOT_PITCH = 7.0
SLOT_MARGIN = 7.0      # solid band above and below the slots
BASKET_HOLE_D = 3.5    # floor holes for roots and water
BASKET_HOLE_PITCH = 6.5

# ---------------------------------------------------------------- hooks
HOOK_W = 20.0          # along the tank wall
HOOK_T = 3.0           # thickness of the hook's top and its riser
RIM_ABOVE_LIP = 0.0    # planter rim height above the lip when it hangs from the hooks
BACK_GAP = 3.5         # planter's back wall to the lip edge; room for the hook's outer leg
SADDLE_L = 15.0        # how far the hook's legs reach down either side of the basket's back wall
SADDLE_T = 2.5         # thickness of those legs
SADDLE_CLEAR = 0.3     # total extra room for the basket wall between them
LEG_T = 3.0            # leg down the outside of the frame
LEG_L = 18.0           # how far it reaches down, below the frame's top edge
LEG_CHAMFER = 1.0      # lead-in on the inside of the leg's tip
HOOK_INSET = 12.0      # from each end of the basket's straight back wall to its hook

# ---------------------------------------------------------------- tray
TRAY_W = 205.0         # along the tank; each half also has to fit the MK4's 210 mm bed width
TRAY_T = 5.0           # plate thickness; its top sits LIP_DROP - TRAY_T below the frame top
TRAY_END_CLEAR = 1.5   # room between each end of the tray and the frame's inner wall
RIB_D = 10.0           # stiffening ribs under the plate, between the lips
RIB_T = 3.0
SEAM_RIB_W = 30.0      # wide rib each side of the joint, holding the keys
HOLE_CLEAR = 0.75      # around the planter in its hole
KEY_W, KEY_H, KEY_L = 14.0, 7.5, 50.0
KEY_CLEAR = 0.3        # on each side of the key in its pocket
KEY_SPACING = 70.0     # three keys: one in the middle and one this far each side

OUT = Path(__file__).parent / "out"

# ------------------------------------------------------------------- layout
CUP_R, CUP_BOTTOM_R = CUP_D / 2, CUP_BOTTOM_D / 2
CUP_Y = -CUP_R                    # cup centre; its rim touches the back plane
BASKET_X0 = CUP_R - BASKET_OVERLAP
BASKET_X1 = BASKET_X0 + BASKET_L
HOOK_XS = (BASKET_X0 + BASKET_CORNER_R + HOOK_INSET + HOOK_W / 2,
           BASKET_X1 - BASKET_CORNER_R - HOOK_INSET - HOOK_W / 2)
TRAY_L = OPENING + 2 * (LIP_W - TRAY_END_CLEAR)   # front to back, both halves
HALF_L = TRAY_L / 2
RIB_END = HALF_L - (LIP_W - TRAY_END_CLEAR) - 2.0  # ribs stop short of the lip
PLANTER_X = -(BASKET_X1 - CUP_R) / 2                # centres the planter along the tray
assert HOOK_XS[1] - HOOK_XS[0] >= HOOK_W + 20, "basket too short for two hooks"
assert BASKET_W <= CUP_D, "the basket should not be wider than the cup"
assert BACK_GAP >= SADDLE_T + SADDLE_CLEAR / 2 + 0.5, "no room for the hook's outer leg"
assert HALF_L <= 250 and TRAY_W <= 210, "a tray half won't fit on the MK4 bed"


def cup_r(z):
    """Outside radius of the cup at height z."""
    return CUP_BOTTOM_R + (CUP_R - CUP_BOTTOM_R) * z / HEIGHT


def cone(r0, r1, z0, z1, x=0.0, y=CUP_Y):
    return Pos(x, y, z0) * Solid.make_cone(r0, r1, z1 - z0)


def rounded_box(x0, x1, y0, y1, z0, z1, r):
    sketch = Pos((x0 + x1) / 2, (y0 + y1) / 2, z0) * RectangleRounded(x1 - x0, y1 - y0, r)
    return extrude(sketch, amount=z1 - z0)


def box(x0, x1, y0, y1, z0, z1):
    return Pos(x0, y0, z0) * Solid.make_box(x1 - x0, y1 - y0, z1 - z0)


def prism_x(yz_pts, x0, width):
    """Extrude a closed (y, z) outline along X, centred on x0."""
    face = make_face(Polyline(*[Vector(x0 - width / 2, y, z) for y, z in yz_pts], close=True))
    return extrude(face, amount=width, dir=(1, 0, 0))


def outline(grow=0.0):
    """The planter's outline at the rim, grown outward by `grow`, as a flat sketch at Z = 0."""
    cup = Pos(0, CUP_Y) * Circle(CUP_R)
    basket = Pos((BASKET_X0 + BASKET_X1) / 2, -BASKET_W / 2) * \
        RectangleRounded(BASKET_L, BASKET_W, BASKET_CORNER_R)
    shape = cup + basket
    return offset(shape, amount=grow) if grow else shape


def hex_grid(pitch, x0, x1, y0, y1):
    """Centres of a hexagonal grid covering a rectangle, centred on it."""
    row_h = pitch * sqrt(3) / 2
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rows = int((y1 - y0) / 2 / row_h) + 1
    cols = int((x1 - x0) / 2 / pitch) + 1
    for j in range(-rows, rows + 1):
        shift = pitch / 2 if j % 2 else 0.0
        for i in range(-cols - 1, cols + 1):
            x, y = cx + i * pitch + shift, cy + j * row_h
            if x0 <= x <= x1 and y0 <= y <= y1:
                yield x, y


def holes(points, d, z0=-1.0, z1=FLOOR + 1.0):
    return [Pos(x, y, z0) * Solid.make_cylinder(d / 2, z1 - z0) for x, y in points]


# ------------------------------------------------------------------- planter
def build_flange():
    """Rim flange on every side but the back plane, with a 45 degree chamfer underneath."""
    chamfer_h = FLANGE_W
    base = Pos(0, 0, HEIGHT - FLANGE_T - chamfer_h) * outline()
    flange = extrude(base, amount=chamfer_h, taper=-45)
    flange += Pos(0, 0, HEIGHT - FLANGE_T) * extrude(outline(FLANGE_W), amount=FLANGE_T)
    return flange & box(-500, 500, -500, 0, 0, HEIGHT)


def build_planter():
    cup_out = cone(CUP_BOTTOM_R, CUP_R, 0, HEIGHT)
    cup_in = cone(cup_r(FLOOR) - WALL, cup_r(HEIGHT + 1) - WALL, FLOOR, HEIGHT + 1)
    basket_out = rounded_box(BASKET_X0, BASKET_X1, -BASKET_W, 0, 0, HEIGHT, BASKET_CORNER_R)
    basket_in = rounded_box(BASKET_X0 + WALL, BASKET_X1 - WALL, -BASKET_W + WALL, -WALL,
                            FLOOR, HEIGHT + 1, BASKET_CORNER_R - WALL)
    body = cup_out + basket_out + build_flange()
    body -= cup_in + (basket_in - cup_out)  # the cup's own wall divides the two

    # floor holes: the cup's inside a margin from its wall, the basket's clear of the cup wall
    floor_r = cup_r(FLOOR) - WALL - 2.0
    cup_pts = [(x, y) for x, y in hex_grid(CUP_HOLE_PITCH, -floor_r, floor_r,
                                            CUP_Y - floor_r, CUP_Y + floor_r)
               if x * x + (y - CUP_Y) ** 2 <= floor_r ** 2]
    m = WALL + 2.0
    keep_out = CUP_BOTTOM_R + 2.0 + BASKET_HOLE_D / 2
    basket_pts = [(x, y) for x, y in hex_grid(BASKET_HOLE_PITCH, BASKET_X0 + m, BASKET_X1 - m,
                                               -BASKET_W + m, -m)
                  if x * x + (y - CUP_Y) ** 2 >= keep_out ** 2]
    body = body.cut(*holes(cup_pts, CUP_HOLE_D), *holes(basket_pts, BASKET_HOLE_D))

    # vertical slots in the basket's flat walls, stopping below the flange's chamfer
    z0, z1 = FLOOR + SLOT_MARGIN, HEIGHT - max(SLOT_MARGIN, FLANGE_T + FLANGE_W + 2)
    flat = BASKET_CORNER_R + SLOT_W
    cutters = []

    def run(a, b):
        n = int((b - a) / SLOT_PITCH)
        start = (a + b) / 2 - n * SLOT_PITCH / 2
        return [start + i * SLOT_PITCH for i in range(n + 1)]

    front_start = sqrt(max(CUP_R ** 2 - (BASKET_W + CUP_Y) ** 2, 0)) + WALL + SLOT_W
    for x in run(front_start, BASKET_X1 - flat):
        cutters.append(box(x - SLOT_W / 2, x + SLOT_W / 2, -BASKET_W - 1, -BASKET_W + WALL + 1,
                           z0, z1))
    # back wall, skipping where the hooks' legs go
    for x in run(BASKET_X0 + flat, BASKET_X1 - flat):
        if all(abs(x - hx) > HOOK_W / 2 + SLOT_W for hx in HOOK_XS):
            cutters.append(box(x - SLOT_W / 2, x + SLOT_W / 2, -WALL - 1, 1, z0, z1))
    for y in run(-BASKET_W + flat, -flat):
        cutters.append(box(BASKET_X1 - WALL - 1, BASKET_X1 + 1, y - SLOT_W / 2, y + SLOT_W / 2,
                           z0, z1))
    return body.cut(*cutters)


# ------------------------------------------------------------------- hooks
def hook_profile():
    """(y, z) outline of a hook, with the lip's edge at y = 0 and the lip's top at z = 0.

    A saddle drops over the basket's back wall, a pad sits on the lip, and an arm reaches over the
    top of the frame to a leg down its outside face. The leg stops the planter swinging in.
    """
    rim = RIM_ABOVE_LIP
    wall_out = -BACK_GAP
    wall_in = wall_out - WALL
    c = SADDLE_CLEAR / 2
    arm_under = LIP_DROP + FRAME_CLEAR
    arm_top = arm_under + HOOK_T
    pad_back = LIP_W - FRAME_CLEAR           # pad stops short of the frame's inner wall
    leg_in = LIP_W + FRAME_TOP_W + FRAME_CLEAR
    leg_out = leg_in + LEG_T
    leg_bottom = arm_under - LEG_L
    top = rim + HOOK_T
    ramp = arm_top - top                     # 45 degree rise from the saddle up to the arm
    return [
        (wall_in - c - SADDLE_T, rim - SADDLE_L), (wall_in - c - SADDLE_T, top),
        (0.0, top), (ramp, arm_top), (leg_out, arm_top), (leg_out, leg_bottom),
        (leg_in + LEG_CHAMFER, leg_bottom), (leg_in, leg_bottom + LEG_CHAMFER), (leg_in, arm_under),
        (pad_back, arm_under), (pad_back, 0.0), (wall_out + c + SADDLE_T, 0.0),
        (wall_out + c + SADDLE_T, rim - SADDLE_L), (wall_out + c, rim - SADDLE_L),
        (wall_out + c, rim), (wall_in - c, rim), (wall_in - c, rim - SADDLE_L),
    ]


def build_hook(x=0.0):
    """A hook in the planter's coordinates, hanging on its back wall at x."""
    return Pos(0, BACK_GAP, HEIGHT - RIM_ABOVE_LIP) * prism_x(hook_profile(), x, HOOK_W)


def lay_flat(part):
    """Turn a part built along X onto its side and set it on the bed."""
    part = Rot(0, -90, 0) * part
    bb = part.bounding_box()
    return Pos(-bb.center().X, -bb.center().Y, -bb.min.Z) * part


# ------------------------------------------------------------------- tray
KEY_XS = (-KEY_SPACING, 0.0, KEY_SPACING)
KEY_Z = (TRAY_T - RIB_D) / 2                # keys sit in the middle of the plate and rib


def planter_back_y():
    """Where the planter's back sits in a tray half: centred between the seam rib and end rib."""
    lo = SEAM_RIB_W + 2 + RIB_T + HOLE_CLEAR + CUP_D   # front of the cup clear of the seam rib
    hi = RIB_END - RIB_T - RIB_T - HOLE_CLEAR          # collar clear of the end rib
    assert lo <= hi, "the planter doesn't fit between the tray's ribs"
    return (lo + hi) / 2


def build_tray_half():
    """One half of the tray, from the seam at Y = 0 to its end on the lip at Y = HALF_L.

    The plate's underside is at Z = 0, level with the lip. Both halves are the same part: the
    other one is turned end for end, so each planter's back faces the nearest tank wall.
    """
    plate = box(-TRAY_W / 2, TRAY_W / 2, 0, HALF_L, 0, TRAY_T)
    ribs = box(-TRAY_W / 2, TRAY_W / 2, 0, SEAM_RIB_W, -RIB_D, 0)
    ribs += box(-TRAY_W / 2, -TRAY_W / 2 + RIB_T, 0, RIB_END, -RIB_D, 0)
    ribs += box(TRAY_W / 2 - RIB_T, TRAY_W / 2, 0, RIB_END, -RIB_D, 0)
    ribs += box(-TRAY_W / 2, TRAY_W / 2, RIB_END - RIB_T, RIB_END, -RIB_D, 0)

    at = Pos(PLANTER_X, planter_back_y())
    collar = at * outline(HOLE_CLEAR + RIB_T)
    ribs += Pos(0, 0, -RIB_D) * extrude(collar, amount=RIB_D)
    half = plate + ribs
    hole = Pos(0, 0, -RIB_D - 1) * extrude(at * outline(HOLE_CLEAR), amount=RIB_D + TRAY_T + 2)
    # countersink for the chamfer under the flange, so the flange sits flat on the plate
    assert FLANGE_W < TRAY_T, "the plate is too thin for the flange's chamfer"
    sink = extrude(Pos(0, 0, TRAY_T - FLANGE_W) * (at * outline(HOLE_CLEAR)),
                   amount=FLANGE_W + 1, taper=-45)
    hole += sink & box(-500, 500, -500, planter_back_y() + HOLE_CLEAR, -50, 50)
    half -= hole

    w, h = KEY_W / 2 + KEY_CLEAR, KEY_H / 2 + KEY_CLEAR
    for x in KEY_XS:
        half -= box(x - w, x + w, -1, KEY_L / 2 + KEY_CLEAR, KEY_Z - h, KEY_Z + h)
    return half


def build_key():
    return box(-KEY_W / 2, KEY_W / 2, -KEY_L / 2, KEY_L / 2, 0, KEY_H)


def tray_assembly():
    """Both tray halves, keys and planters in place, centred front to back on Y = 0."""
    half = build_tray_half()
    planter = Pos(PLANTER_X, planter_back_y(), TRAY_T - HEIGHT + FLANGE_T) * build_planter()
    parts = [half, Rot(0, 0, 180) * half, planter, Rot(0, 0, 180) * planter]
    keys = [Pos(x, 0, KEY_Z - KEY_H / 2) * build_key() for x in KEY_XS]
    return parts, keys


def main():
    OUT.mkdir(exist_ok=True)
    planter = build_planter()
    export_stl(planter, OUT / "planter.stl")
    export_step(planter, OUT / "aquarium_planter.step")
    export_stl(lay_flat(prism_x(hook_profile(), 0, HOOK_W)), OUT / "hook.stl")

    half = build_tray_half()
    export_step(half, OUT / "tray_half.step")
    upside_down = Rot(180, 0, 0) * half
    export_stl(Pos(0, 0, -upside_down.bounding_box().min.Z) * upside_down, OUT / "tray_half.stl")
    export_stl(build_key(), OUT / "tray_key.stl")

    for name, part in (("planter", planter), ("tray half", half)):
        bb = part.bounding_box()
        print(f"{name}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, "
              f"{part.volume / 1000:.1f} cm3, solids={len(part.solids())}, valid={part.is_valid}")
    print(f"tray {TRAY_W:.0f} x {TRAY_L:.1f} mm in two halves; planter back at "
          f"{planter_back_y():.1f} mm from the seam")


if __name__ == "__main__":
    main()
