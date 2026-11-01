"""Render preview images of the tip cup from the STLs in ./out."""

from pathlib import Path

import pyvista as pv

from tip_cup import CUP_H, SHORT_CUP_H

OUT = Path(__file__).parent / "out"
CREAM, BROWN, LID_BROWN = "#ece4d6", "#8a6142", "#6e4c38"


def load_lid(seat_z):
    lid = pv.read(OUT / "lid.stl")  # stored top-down for printing; flip back
    lid = lid.rotate_x(180, inplace=False)
    return lid.translate((0, 0, seat_z - lid.bounds[4]), inplace=False)


def load():
    cup = pv.read(OUT / "cup.stl")
    sleeve = pv.read(OUT / "sleeve.stl")
    return cup, sleeve, load_lid(CUP_H)


def shot(meshes, path, camera, size=(900, 1100), zoom=1.0):
    p = pv.Plotter(off_screen=True, window_size=size)
    p.set_background("#b9b9bd")
    for mesh, color in meshes:
        p.add_mesh(mesh, color=color, smooth_shading=True, split_sharp_edges=True,
                   feature_angle=25, specular=0.25)
    p.remove_all_lights()
    p.add_light(pv.Light(position=(-400, -300, 450), focal_point=(0, 0, 100), intensity=0.9))
    p.add_light(pv.Light(position=(400, -200, 100), focal_point=(0, 0, 100), intensity=0.35))
    p.add_light(pv.Light(light_type="headlight", intensity=0.25))
    p.camera_position = camera
    p.camera.zoom(zoom)
    p.screenshot(path)
    p.close()


def main():
    cup, sleeve, lid = load()
    parts = [(cup, CREAM), (sleeve, BROWN), (lid, LID_BROWN)]
    c = (0, 0, 100)
    shot(parts, OUT / "preview_front.png", [(0, -520, 160), c, (0, 0, 1)])
    shot(parts, OUT / "preview_back.png", [(250, 450, 220), c, (0, 0, 1)])

    up = 70
    exploded = [(cup, CREAM), (sleeve.translate((0, 0, 0), inplace=False), BROWN),
                (lid.translate((0, 0, up), inplace=False), LID_BROWN)]
    shot(exploded, OUT / "preview_exploded.png", [(330, -520, 260), (0, 0, 135), (0, 0, 1)])
    shot([(lid, LID_BROWN)], OUT / "preview_lid_top.png",
         [(0, -120, 420), (0, 0, 180), (0, 0, 1)], size=(900, 900))

    shot(parts, OUT / "preview_sleeve.png", [(0, -260, 78), (0, 0, 78), (0, 0, 1)],
         size=(900, 700), zoom=1.6)

    short = [(pv.read(OUT / "cup_short.stl"), CREAM), (load_lid(SHORT_CUP_H), LID_BROWN)]
    c = (0, 0, 70)
    shot(short, OUT / "preview_short_front.png", [(0, -430, 130), c, (0, 0, 1)],
         size=(900, 900))
    shot(short, OUT / "preview_short_angle.png", [(260, -330, 230), c, (0, 0, 1)],
         size=(900, 900))

    print("rendered previews to", OUT)


if __name__ == "__main__":
    main()
