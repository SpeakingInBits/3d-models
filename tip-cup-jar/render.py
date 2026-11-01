"""Render preview images of the tip cup from the STLs in ./out."""

from pathlib import Path

import pyvista as pv

from tip_cup import CUP_H

OUT = Path(__file__).parent / "out"
CREAM, LID_BROWN = "#ece4d6", "#6e4c38"


def load():
    cup = pv.read(OUT / "cup.stl")
    lid = pv.read(OUT / "lid.stl")  # stored top-down for printing; flip back
    lid = lid.rotate_x(180, inplace=False)
    lid = lid.translate((0, 0, CUP_H - lid.bounds[4]), inplace=False)
    return cup, lid


def shot(meshes, path, camera, size=(900, 900), zoom=1.0):
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
    cup, lid = load()
    parts = [(cup, CREAM), (lid, LID_BROWN)]
    c = (0, 0, 70)
    shot(parts, OUT / "preview_front.png", [(0, -430, 130), c, (0, 0, 1)])
    shot(parts, OUT / "preview_angle.png", [(260, -330, 230), c, (0, 0, 1)])

    exploded = [(cup, CREAM), (lid.translate((0, 0, 60), inplace=False), LID_BROWN)]
    shot(exploded, OUT / "preview_exploded.png", [(330, -480, 220), (0, 0, 95), (0, 0, 1)],
         size=(900, 1100))
    shot([(lid, LID_BROWN)], OUT / "preview_lid_top.png",
         [(0, -120, CUP_H + 320), (0, 0, CUP_H + 30), (0, 0, 1)])
    print("rendered previews to", OUT)


if __name__ == "__main__":
    main()
