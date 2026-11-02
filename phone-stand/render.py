"""Render preview images of the stand from the STLs in ./out, with a stand-in phone and watch."""

from pathlib import Path

import pyvista as pv

from phone_stand import (
    MAGSAFE_D, MAGSAFE_POCKET, PAD_TILT, PHONE_T, TILT, WATCH_D, WATCH_POCKET,
    pad, s_magsafe, s_watch, tower,
)

OUT = Path(__file__).parent / "out"
STAND, PHONE, PUCK, WATCH = "#d9d4cc", "#3b3f46", "#f4f4f2", "#8a8f98"
PHONE_W, PHONE_H = 77.6, 160.7


def on_face(mesh, face, tilt, s, out):
    """Move a mesh built lying in the XY plane (facing +Z = outward) onto a sloped face."""
    mesh = mesh.rotate_x(90 - tilt, inplace=False)  # +Z turns to the face normal
    return mesh.translate(tuple(face.point(s, out)), inplace=False)


def puck(d, thick, proud):
    disc = pv.Cylinder(center=(0, 0, proud - thick / 2), direction=(0, 0, 1), radius=d / 2,
                       height=thick, resolution=96)
    return disc


def scene():
    stand = pv.read(OUT / "stand.stl")
    mag_proud = 5.3 - MAGSAFE_POCKET
    watch_proud = 7.0 - WATCH_POCKET
    mag = on_face(puck(MAGSAFE_D, 5.3, mag_proud), tower, TILT, s_magsafe, 0)
    wpuck = on_face(puck(WATCH_D, 7.0, watch_proud), pad, PAD_TILT, s_watch, 0)

    # phone centred on the MagSafe puck, its back resting on the puck face
    phone = pv.Box(bounds=(-PHONE_W / 2, PHONE_W / 2, -PHONE_H / 2, PHONE_H / 2, 0, PHONE_T))
    phone = on_face(phone, tower, TILT, s_magsafe - (PHONE_H / 2 - 80.35), mag_proud)

    # watch on its side: 45 mm case, 38 mm across, band reaching out left and right
    case = pv.Box(bounds=(-22.5, 22.5, -19, 19, 0, 10.7))
    band = pv.Box(bounds=(-60, 60, -12, 12, 3, 6))
    watch = on_face(case, pad, PAD_TILT, s_watch, watch_proud)
    band = on_face(band, pad, PAD_TILT, s_watch, watch_proud)
    return stand, [(mag, PUCK), (wpuck, PUCK), (phone, PHONE), (watch, WATCH), (band, WATCH)]


def shot(meshes, path, camera, size=(1000, 800), zoom=1.0):
    p = pv.Plotter(off_screen=True, window_size=size)
    p.set_background("#b9b9bd")
    for mesh, color in meshes:
        p.add_mesh(mesh, color=color, smooth_shading=True, split_sharp_edges=True,
                   feature_angle=25, specular=0.25)
    p.remove_all_lights()
    p.add_light(pv.Light(position=(-400, -400, 450), focal_point=(40, 30, 50), intensity=0.9))
    p.add_light(pv.Light(position=(400, -200, 100), focal_point=(40, 30, 50), intensity=0.35))
    p.add_light(pv.Light(light_type="headlight", intensity=0.25))
    p.camera_position = camera
    p.camera.zoom(zoom)
    p.screenshot(path)
    p.close()


def main():
    stand, extras = scene()
    c = (28, 30, 55)
    shot([(stand, STAND)], OUT / "preview_stand.png", [(260, -330, 260), c, (0, 0, 1)])
    shot([(stand, STAND)] + extras, OUT / "preview_in_use.png",
         [(280, -360, 240), (28, 20, 80), (0, 0, 1)], size=(1000, 1000))
    shot([(stand, STAND)] + extras, OUT / "preview_side.png",
         [(450, 30, 80), (28, 30, 70), (0, 0, 1)], size=(1000, 900))
    shot([(stand, STAND)], OUT / "preview_bottom.png", [(150, -200, -380), (28, 30, 0), (0, 0, 1)])
    print("rendered previews to", OUT)


if __name__ == "__main__":
    main()
