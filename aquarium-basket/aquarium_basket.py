"""Aquarium plant basket: a grid-walled box, like a dishwasher's cutlery basket, that hangs inside a
framed tank against its end wall from two hooks built into its back wall. Two of them fill the end
wall side by side.

All dimensions are in millimetres. Change the parameters below and re-run from the repo root:

    .venv/Scripts/python aquarium-basket/aquarium_basket.py

Outputs go to aquarium-basket/out:
    basket.stl   - print 2, open top up, with supports from the build plate under the two hooks
    aquarium_basket.step - the basket, for viewing/editing in other CAD tools

Axes: X runs along the tank wall, Y points out through the tank wall, Z up. The basket is built with
its back wall's outside face at Y = 0 and its rim at Z = HEIGHT.
"""

from pathlib import Path

from build123d import (
    Polyline, Pos, RectangleRounded, Solid, Vector, export_step, export_stl, extrude, make_face,
)

# ---------------------------------------------------------------- tank frame
LIP_DROP = 8.5         # how far the lip is below the top edge of the frame
LIP_W = 10.0           # how far the lip sticks into the tank from the frame's inner wall
FRAME_TOP_W = 13.3     # across the frame top, inner wall to outer face: 9/16 in less 1 mm to grip
OPENING = 287.0        # along the end wall, between the front and back lip edges
FRAME_CLEAR = 0.8      # room around the frame in the hooks

# ---------------------------------------------------------------- basket
HEIGHT = 139.7         # 5.5 in, bottom to rim
DEPTH = 88.9           # 3.5 in, out from the tank wall
COUNT = 2              # baskets side by side along the end wall; their length is worked out to fit
END_CLEAR = 12.0       # room between the outer baskets and the front and back lips
BETWEEN = 8.0          # room between neighbouring baskets; both are generous in case OPENING is off
WALL = 2.0
FLOOR = 2.4
CORNER_R = 5.0
GRID_OPENING = 8.0     # square openings in the walls; their tops are short bridges when printing
GRID_BAR = 2.6         # bars between them
FLOOR_OPENING = 6.0    # square openings in the floor, smaller to hold gravel or clay pebbles
TOP_BAND = 6.0         # solid band around the rim
BOTTOM_BAND = 6.0      # solid band around the bottom
CORNER_BAND = 6.0      # solid strip either side of each corner

# ---------------------------------------------------------------- hooks
HOOK_W = 20.0          # along the tank wall
HOOK_T = 3.0           # thickness of the hook's top and its riser
RIM_ABOVE_LIP = 0.0    # basket rim height above the lip
BACK_GAP = 1.0         # basket's back wall to the lip edge
HOOK_ROOT = 12.0       # how far down the back wall the hook is joined on; the wall is solid there
GUSSET = 5.0           # thickening inside the back wall under each hook, so the wall doesn't bend
LEG_T = 3.0            # leg down the outside of the frame
LEG_L = 18.0           # how far it reaches down, below the frame's top edge
LEG_CHAMFER = 1.0      # lead-in on the inside of the leg's tip
HOOK_INSET = 20.0      # from each end of the basket to the middle of its hook

OUT = Path(__file__).parent / "out"

# ------------------------------------------------------------------- layout
LENGTH = (OPENING - 2 * END_CLEAR - (COUNT - 1) * BETWEEN) / COUNT
HOOK_XS = (-LENGTH / 2 + HOOK_INSET, LENGTH / 2 - HOOK_INSET)
assert HOOK_XS[1] - HOOK_XS[0] >= HOOK_W + 20, "basket too short for two hooks"
assert HOOK_ROOT >= GUSSET + 4 and RIM_ABOVE_LIP < HOOK_ROOT, "the hook's root is too short"
assert LENGTH <= 250 and DEPTH + BACK_GAP + LIP_W + FRAME_TOP_W + 5 <= 210     and HEIGHT + LIP_DROP + 5 <= 220, "the basket won't fit on the MK4"


def box(x0, x1, y0, y1, z0, z1):
    return Pos(x0, y0, z0) * Solid.make_box(x1 - x0, y1 - y0, z1 - z0)


def rounded_box(x0, x1, y0, y1, z0, z1, r):
    sketch = Pos((x0 + x1) / 2, (y0 + y1) / 2, z0) * RectangleRounded(x1 - x0, y1 - y0, r)
    return extrude(sketch, amount=z1 - z0)


def prism_x(yz_pts, x0, width):
    """Extrude a closed (y, z) outline along X, centred on x0."""
    face = make_face(Polyline(*[Vector(x0 - width / 2, y, z) for y, z in yz_pts], close=True))
    return extrude(face, amount=width, dir=(1, 0, 0))


def spread(a, b, opening, bar):
    """Centres of evenly spaced openings filling a to b, with at least `bar` between them.

    Returns the centres and the opening size, stretched a little so the bars come out even.
    """
    n = int((b - a + bar) // (opening + bar))
    if n < 1:
        return [], opening
    size = (b - a - (n - 1) * bar) / n
    return [a + size / 2 + i * (size + bar) for i in range(n)], size


# ------------------------------------------------------------------- basket
def build_basket():
    x0, x1, y0, y1 = -LENGTH / 2, LENGTH / 2, -DEPTH, 0.0
    body = rounded_box(x0, x1, y0, y1, 0, HEIGHT, CORNER_R)
    body -= rounded_box(x0 + WALL, x1 - WALL, y0 + WALL, y1 - WALL, FLOOR, HEIGHT + 1,
                        CORNER_R - WALL)

    rows, row_h = spread(BOTTOM_BAND, HEIGHT - TOP_BAND, GRID_OPENING, GRID_BAR)
    edge = CORNER_R + CORNER_BAND
    cols_x, col_w = spread(x0 + edge, x1 - edge, GRID_OPENING, GRID_BAR)
    cols_y, col_d = spread(y0 + edge, y1 - edge, GRID_OPENING, GRID_BAR)
    root_bottom = HEIGHT - HOOK_ROOT - 2

    cutters = []
    for z in rows:
        z_lo, z_hi = z - row_h / 2, z + row_h / 2
        for x in cols_x:
            a, b = x - col_w / 2, x + col_w / 2
            cutters.append(box(a, b, y0 - 1, y0 + WALL + 1, z_lo, z_hi))           # front
            under_hook = any(abs(x - hx) < HOOK_W / 2 + col_w / 2 + 1 for hx in HOOK_XS)
            if not (under_hook and z_hi > root_bottom):                              # back
                cutters.append(box(a, b, y1 - WALL - 1, y1 + 1, z_lo, z_hi))
        for y in cols_y:
            a, b = y - col_d / 2, y + col_d / 2
            cutters.append(box(x0 - 1, x0 + WALL + 1, a, b, z_lo, z_hi))           # ends
            cutters.append(box(x1 - WALL - 1, x1 + 1, a, b, z_lo, z_hi))

    m = WALL + 2.0
    fx, fw = spread(x0 + m, x1 - m, FLOOR_OPENING, GRID_BAR)
    fy, fd = spread(y0 + m, y1 - m, FLOOR_OPENING, GRID_BAR)
    for x in fx:
        for y in fy:
            cutters.append(box(x - fw / 2, x + fw / 2, y - fd / 2, y + fd / 2, -1, FLOOR + 1))
    body = body.cut(*cutters)
    for x in HOOK_XS:
        body += build_hook(x)
    return body


# ------------------------------------------------------------------- hooks
def hook_profile():
    """(y, z) outline of a hook, with the lip's edge at y = 0 and the lip's top at z = 0.

    It grows out of the top of the basket's back wall, with a gusset inside the wall. A pad sits on
    the lip, and an arm reaches over the top of the frame to a leg down its outside face. The frame
    is gripped between the pad and the leg, which stops the basket tipping into the tank.
    """
    rim = RIM_ABOVE_LIP
    wall_out = -BACK_GAP
    wall_in = wall_out - WALL
    arm_under = LIP_DROP + FRAME_CLEAR
    arm_top = arm_under + HOOK_T
    pad_back = LIP_W - FRAME_CLEAR           # pad stops short of the frame's inner wall
    leg_in = LIP_W + FRAME_TOP_W + FRAME_CLEAR
    leg_out = leg_in + LEG_T
    leg_bottom = arm_under - LEG_L
    top = rim + HOOK_T
    ramp = arm_top - top                     # 45 degree rise from the rim up to the arm
    return [
        (wall_in - GUSSET, top), (0.0, top), (ramp, arm_top), (leg_out, arm_top),
        (leg_out, leg_bottom), (leg_in + LEG_CHAMFER, leg_bottom),
        (leg_in, leg_bottom + LEG_CHAMFER), (leg_in, arm_under), (pad_back, arm_under),
        (pad_back, 0.0), (wall_out, 0.0), (wall_out, rim - HOOK_ROOT), (wall_in, rim - HOOK_ROOT),
        (wall_in, rim - 3 - GUSSET), (wall_in - GUSSET, rim - 3),   # 45 degrees under the gusset
    ]


def build_hook(x=0.0):
    """A hook in the basket's coordinates, on its back wall at x."""
    return Pos(0, BACK_GAP, HEIGHT - RIM_ABOVE_LIP) * prism_x(hook_profile(), x, HOOK_W)


def main():
    OUT.mkdir(exist_ok=True)
    basket = build_basket()
    export_stl(basket, OUT / "basket.stl")
    export_step(basket, OUT / "aquarium_basket.step")
    bb = basket.bounding_box()
    print(f"basket: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, "
          f"{basket.volume / 1000:.1f} cm3, solids={len(basket.solids())}, valid={basket.is_valid}")
    print(f"{COUNT} baskets {LENGTH:.1f} mm long fill {OPENING:.0f} mm with {END_CLEAR:.0f} mm at "
          f"each end and {BETWEEN:.0f} mm between")


if __name__ == "__main__":
    main()
