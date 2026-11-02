"""Phone and watch charging stand: an Apple MagSafe charger for an iPhone 14 Pro Max in portrait
on a tilted tower, and an Apple Watch charger on a 45 degree pad beside it.

All dimensions are in millimetres. Change the parameters below and re-run from the repo root:

    .venv/Scripts/python phone-stand/phone_stand.py

Outputs go to phone-stand/out:
    stand.stl     - print flat on its base, no supports
    fit_test.stl  - both charger pockets in a thin plate, to check the fit before the full print
    phone_stand.step - the stand, for viewing/editing in other CAD tools

Axes: X runs left to right, Y from front to back, Z up. The phone faces -Y.
"""

from math import cos, sin, radians, tan
from pathlib import Path

from build123d import (
    Axis, Circle, Location, Plane, Polyline, Pos, RectangleRounded, Solid, Vector,
    chamfer, export_step, export_stl, extrude, fillet, loft, make_face,
)

# ---------------------------------------------------------------- phone (iPhone 14 Pro Max, no case)
PHONE_T = 7.85
MAGSAFE_FROM_BOTTOM = 80.35  # centre of the phone's MagSafe ring above its bottom edge
CAMERA_FROM_BOTTOM = 117.0   # where the camera bump starts; the tower has to stop below it

# ---------------------------------------------------------------- chargers
# Apple's pucks vary by model, so each puck stands a little proud of the surface to be sure it
# touches the phone or watch. Crush ribs take up small differences in diameter.
MAGSAFE_D = 55.9       # original MagSafe Charger (2020) 55.9; 2024 25 W model 55.5
MAGSAFE_POCKET = 4.6   # original puck (5.3 thick) stands 0.7 proud; use 3.9 for the 4.45 thick 25 W
WATCH_D = 27.6         # Apple Watch charger puck, about 27.5-28
WATCH_POCKET = 5.5     # puck is 6.5-8.2 thick depending on the model
POCKET_CLEAR = 0.4     # diametral clearance before ribs
RIB_PROTRUDE = 0.4     # how far each crush rib stands out from the pocket wall
RIB_R = 0.8
RIB_ANGLES = (0, 45, 135, 180)  # sides and lower diagonals; the top of the pocket is flared
MAX_OVERHANG = 40.0    # steepest overhang from vertical; the top of each pocket flares to stay under it
CABLE_SLOT_W = 4.2     # cable is about 3.3 thick and presses in from the open side
RELIEF_W, RELIEF_L = 6.5, 12.0  # wider slot where the cable's strain relief leaves the puck
CABLE_SLOT_D = 6.0     # slot depth into the face

# ---------------------------------------------------------------- base
BASE_T = 10.0
BASE_CORNER_R = 10.0
FRONT_MARGIN = 2.0     # base sticks out past the lip so the lip doesn't overhang the edge chamfer
SIDE_MARGIN = 8.0
REAR_MARGIN = 10.0
GROOVE_D = 6.0         # cable grooves under the base
FOOT_D, FOOT_DEPTH, FOOT_INSET = 13.0, 1.0, 13.0  # recesses for 12.7 mm (1/2 in) rubber bumpers

# ---------------------------------------------------------------- phone tower
TILT = 25.0            # lean back from vertical
TOWER_W = 72.0
TOWER_T = 12.0         # plate thickness measured normal to the face
LEDGE_DROP = 1.5       # ledge sits this far below the phone so the magnets, not the ledge, align it
LEDGE_D = PHONE_T + 2.5
LIP_T, LIP_H = 3.0, 6.0

# ---------------------------------------------------------------- watch pad
PAD_TILT = 45.0
PAD_W = 34.0
PAD_GAP = 28.0         # room between tower and pad for the watch band to hang
PAD_CENTRE_H = 40.0    # height of the watch puck centre above the base
PAD_TOP_FLAT = 6.0
PAD_FOOT_Y = -4.0      # where the pad's face meets the base

OUT = Path(__file__).parent / "out"


class SlopedFace:
    """A flat face leaning back by `tilt` degrees, rising from the base top at (x0, y0).

    Positions on it are given as s, the distance up the slope from the base top.
    """

    def __init__(self, x0, y0, tilt, z0=BASE_T):
        self.tilt = tilt
        t = radians(tilt)
        self.origin = Vector(x0, y0, z0)
        self.up = Vector(0, sin(t), cos(t))
        self.normal = Vector(0, -cos(t), sin(t))  # points out of the face

    def point(self, s, out=0.0):
        return self.origin + self.up * s + self.normal * out

    def plane(self, s, out=0.0):
        """Plane on the face: local x = world X, local y = up the slope, local z = outward."""
        return Plane(origin=self.point(s, out), x_dir=(1, 0, 0), z_dir=self.normal)


def prism_x(yz_pts, x0, width):
    """Extrude a closed (y, z) outline along X, centred on x0."""
    face = make_face(Polyline(*[Vector(x0, y, z) for y, z in yz_pts], close=True))
    return extrude(face, amount=width / 2, both=True)


def box_on(plane, x, y, z, cx=0.0, cy=0.0, cz=0.0):
    """Box of size x*y*z centred at (cx, cy, cz) in a plane's local coordinates."""
    return plane.location * Location((cx - x / 2, cy - y / 2, cz - z / 2)) * Solid.make_box(x, y, z)


def puck_pocket(face, s_centre, diameter, depth):
    """Pocket for a round charger with crush ribs and a cable slot running down the slope.

    On a face leaning back less than 90 - MAX_OVERHANG degrees, the top of the pocket wall would be
    an overhang, so the top of the pocket is sheared up the slope toward the face to stay printable.

    Returns (cutter, ribs): subtract the cutter, then add the ribs.
    """
    r = (diameter + POCKET_CLEAR) / 2
    # local x = world X, local y = down the slope, local z = into the face
    into = Plane(origin=face.point(s_centre, 1.0), x_dir=(1, 0, 0), z_dir=-face.normal)
    length = depth + 1.0
    cutter = Solid.make_cylinder(r, length, into)
    flare = max(0.0, 90 - MAX_OVERHANG - face.tilt)
    if flare:
        shift = length * tan(radians(flare))
        cutter += loft([into * Pos(0, -shift, 0) * Circle(r), into * Pos(0, 0, length) * Circle(r)])

    # cable slot from the puck centre down to the base, wider at the strain relief
    p = face.plane(0)
    cutter += box_on(p, CABLE_SLOT_W, s_centre, CABLE_SLOT_D + 2, cy=s_centre / 2,
                     cz=1 - CABLE_SLOT_D / 2)
    cutter += box_on(p, RELIEF_W, RELIEF_L, CABLE_SLOT_D + 2, cy=s_centre - r - RELIEF_L / 2 + 1,
                     cz=1 - CABLE_SLOT_D / 2)

    ribs = None
    for ang in RIB_ANGLES:
        a = radians(ang)
        local = Location((cos(a) * (r - RIB_PROTRUDE + RIB_R), sin(a) * (r - RIB_PROTRUDE + RIB_R),
                          1.0))
        rib = into.location * local * Solid.make_cylinder(RIB_R, depth)
        ribs = rib if ribs is None else ribs + rib
    return cutter, ribs


def through_slot(x, y, tilt):
    """Vertical slot through the base where a cable drops from a face slot to the underside.

    It runs from just in front of the face's foot to the back of the face slot.
    """
    length = 3 + CABLE_SLOT_D / cos(radians(tilt)) + 1
    return Pos(x - CABLE_SLOT_W / 2, y - 3, -1) * Solid.make_box(CABLE_SLOT_W, length, BASE_T + 4)


# ------------------------------------------------------------------- layout
tower = SlopedFace(0, 0, TILT)
s_magsafe = MAGSAFE_FROM_BOTTOM + LEDGE_DROP  # puck centre, up the slope from the ledge floor
s_tower_top = s_magsafe + MAGSAFE_D / 2 + 3
assert s_tower_top < CAMERA_FROM_BOTTOM + LEDGE_DROP, "tower would hit the camera bump"

pad_x = TOWER_W / 2 + PAD_GAP + PAD_W / 2
pad = SlopedFace(pad_x, PAD_FOOT_Y, PAD_TILT)
s_watch = PAD_CENTRE_H / cos(radians(PAD_TILT))
s_pad_top = s_watch + WATCH_D / 2 + 5

x_left = -TOWER_W / 2 - SIDE_MARGIN
x_right = pad_x + PAD_W / 2 + SIDE_MARGIN
y_front = -LEDGE_D - LIP_T  # front of the lip
y_base_front = y_front - FRONT_MARGIN
tower_back = (tower.point(s_tower_top) - tower.normal * TOWER_T).Y
pad_back = pad.point(s_pad_top).Y + PAD_TOP_FLAT
y_rear = max(tower_back, pad_back) + REAR_MARGIN


def build_tower():
    top_front = tower.point(s_tower_top)
    top_back = top_front - tower.normal * TOWER_T
    foot = tower.point(-(BASE_T - 1) / cos(radians(TILT)))  # reach down into the base to fuse
    pts = [(foot.Y, foot.Z), (top_front.Y, top_front.Z), (top_back.Y, top_back.Z),
           (top_back.Y, 1.0)]
    body = prism_x(pts, 0, TOWER_W)
    top_edges = body.edges().filter_by(Axis.X).sort_by(Axis.Z)[-2:]
    body = fillet(top_edges, 3.0)
    side_edges = body.edges().filter_by(lambda e: abs(e.tangent_at(0.5).X) < 0.1) \
        .filter_by(lambda e: e.center().Z > BASE_T + 2)
    return fillet(side_edges, 2.0)


def build_pad():
    top_front = pad.point(s_pad_top)
    foot = pad.point(-(BASE_T - 1) / cos(radians(PAD_TILT)))
    pts = [(foot.Y, foot.Z), (top_front.Y, top_front.Z), (top_front.Y + PAD_TOP_FLAT, top_front.Z),
           (top_front.Y + PAD_TOP_FLAT, 1.0)]
    body = prism_x(pts, pad_x, PAD_W)
    top_edges = body.edges().filter_by(Axis.X).sort_by(Axis.Z)[-2:]
    body = fillet(top_edges, 2.5)
    side_edges = body.edges().filter_by(lambda e: abs(e.tangent_at(0.5).X) < 0.1) \
        .filter_by(lambda e: e.center().Z > BASE_T + 2)
    return fillet(side_edges, 2.0)


def build_base():
    w, d = x_right - x_left, y_rear - y_base_front
    plate = Pos((x_left + x_right) / 2, (y_base_front + y_rear) / 2) * extrude(
        RectangleRounded(w, d, BASE_CORNER_R), amount=BASE_T)
    plate = chamfer(plate.edges().group_by(Axis.Z)[-1], 1.5)
    plate = chamfer(plate.edges().group_by(Axis.Z)[0], 0.6)  # elephant-foot relief

    lip = Pos(-TOWER_W / 2, y_front, BASE_T - 1) * Solid.make_box(TOWER_W, LIP_T, LIP_H + 1)
    lip = fillet(lip.edges().filter_by(Axis.X).sort_by(Axis.Z)[-2:], 1.4)
    return plate + lip


def underside_cuts():
    cuts = None
    for x, y, tilt in ((0, 0, TILT), (pad_x, PAD_FOOT_Y, PAD_TILT)):
        groove = Pos(x - CABLE_SLOT_W / 2, y - 3, -1) * Solid.make_box(
            CABLE_SLOT_W, y_rear - y + 5, GROOVE_D + 1)
        cut = through_slot(x, y, tilt) + groove
        cuts = cut if cuts is None else cuts + cut
    for x in (x_left + FOOT_INSET, x_right - FOOT_INSET):
        for y in (y_base_front + FOOT_INSET, y_rear - FOOT_INSET):
            cuts += Pos(x, y, -1) * Solid.make_cylinder(FOOT_D / 2, FOOT_DEPTH + 1)
    return cuts


def build_stand():
    stand = build_base() + build_tower() + build_pad()
    for face, s, d, depth in ((tower, s_magsafe, MAGSAFE_D, MAGSAFE_POCKET),
                              (pad, s_watch, WATCH_D, WATCH_POCKET)):
        cutter, ribs = puck_pocket(face, s, d, depth)
        stand = stand - cutter + ribs
    return stand - underside_cuts()


def build_fit_test():
    """Both pockets in flat plates with 2 mm floors and the cable slots, for a quick test print."""
    part = None
    cx = 0.0
    for d, depth in ((MAGSAFE_D, MAGSAFE_POCKET), (WATCH_D, WATCH_POCKET)):
        size, t = d + 10, depth + 2.0
        plate = Pos(cx, size / 2) * extrude(RectangleRounded(size, size, 5), amount=t)
        cutter, rib_solids = puck_pocket(SlopedFace(cx, 0, 90, z0=t), size / 2, d, depth)
        plate = plate - cutter + rib_solids
        part = plate if part is None else part + plate
        cx += size / 2 + 8 + (WATCH_D + 10) / 2
    return part


def main():
    OUT.mkdir(exist_ok=True)
    print("building stand...")
    stand = build_stand()
    print("building fit test...")
    fit = build_fit_test()
    for name, part in (("stand", stand), ("fit_test", fit)):
        bb = part.bounding_box()
        print(f"  {name}: valid={part.is_valid}, volume={part.volume / 1000:.1f} cm^3, "
              f"size={bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}")

    export_stl(stand, OUT / "stand.stl", tolerance=0.01, angular_tolerance=0.1)
    export_stl(fit, OUT / "fit_test.stl", tolerance=0.01, angular_tolerance=0.1)
    export_step(stand, OUT / "phone_stand.step")
    print("done ->", OUT)


if __name__ == "__main__":
    main()
