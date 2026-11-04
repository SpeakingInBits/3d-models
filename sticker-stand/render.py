"""Render preview images of the sticker stand from the STL in ./out."""

from pathlib import Path

import pyvista as pv

from sticker_stand import STAND_H

OUT = Path(__file__).parent / "out"
STAND = "#ece4d6"


def shot(mesh, path, camera, size=(1000, 700), zoom=1.0, side=1):
    """side=-1 swings the lights around to the back of the stand."""
    p = pv.Plotter(off_screen=True, window_size=size)
    p.set_background("#b9b9bd")
    p.add_mesh(mesh, color=STAND, smooth_shading=True, split_sharp_edges=True, feature_angle=25,
               specular=0.25)
    p.remove_all_lights()
    p.add_light(pv.Light(position=(-300 * side, -400 * side, 450), focal_point=(0, 0, 25), intensity=0.9))
    p.add_light(pv.Light(position=(400 * side, -200 * side, 100), focal_point=(0, 0, 25), intensity=0.35))
    p.add_light(pv.Light(light_type="headlight", intensity=0.25))
    p.camera_position = camera
    p.camera.zoom(zoom)
    p.screenshot(path)
    p.close()


def main():
    stand = pv.read(OUT / "stand.stl")
    c = (0, 0, STAND_H / 2)
    shot(stand, OUT / "preview_angle.png", [(190, -300, 170), c, (0, 0, 1)], zoom=1.7)
    shot(stand, OUT / "preview_front.png", [(0, -380, 130), c, (0, 0, 1)], zoom=1.8)
    shot(stand, OUT / "preview_back.png", [(-190, 300, 170), c, (0, 0, 1)], zoom=1.7, side=-1)
    shot(stand, OUT / "preview_side.png", [(380, 0, STAND_H / 2), c, (0, 0, 1)], zoom=2.0)
    print("rendered previews to", OUT)


if __name__ == "__main__":
    main()
