"""Render preview images of the basket, and two of them hanging on a stand-in tank end wall."""

import tempfile
from pathlib import Path

import pyvista as pv
from build123d import Pos, export_stl

import aquarium_basket as ab

OUT = Path(__file__).parent / "out"
PLASTIC, HOOK, FRAME, GLASS, WATER = "#ecebe6", "#f2c14e", "#2b2d31", "#a9d4e0", "#4f8fb8"


def mesh(part):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "part.stl"
        export_stl(part, path)
        return pv.read(path)


def tank_end(lip_z):
    """The end wall's frame and glass, plus the front and back lips at each corner."""
    half = ab.OPENING / 2
    x0, x1 = -half - ab.LIP_W, half + ab.LIP_W
    y = ab.BACK_GAP  # lip edge, in the baskets' coordinates
    lip = pv.Box(bounds=(x0, x1, y, y + ab.LIP_W, lip_z - 4, lip_z))
    top = pv.Box(bounds=(x0 - ab.FRAME_TOP_W, x1 + ab.FRAME_TOP_W, y + ab.LIP_W,
                         y + ab.LIP_W + ab.FRAME_TOP_W, lip_z - 30, lip_z + ab.LIP_DROP))
    glass = pv.Box(bounds=(x0, x1, y + ab.LIP_W + 4, y + ab.LIP_W + 10, lip_z - 220, lip_z - 30))
    sides = [pv.Box(bounds=(s * half, s * (half + ab.LIP_W), y - 140, y + ab.LIP_W, lip_z - 4, lip_z))
             for s in (-1, 1)]
    frame = lip + top + sides[0] + sides[1]
    water = pv.Box(bounds=(x0, x1, y - 140, y + ab.LIP_W + 4, lip_z - 220, lip_z - 22))
    return [(frame, FRAME, 1.0), (glass, GLASS, 0.35), (water, WATER, 0.3)]


def shot(meshes, path, camera, size=(1000, 800), zoom=1.0):
    p = pv.Plotter(off_screen=True, window_size=size)
    p.set_background("#b9b9bd")
    for m, color, opacity in meshes:
        p.add_mesh(m, color=color, opacity=opacity, smooth_shading=True,
                   split_sharp_edges=True, feature_angle=25, specular=0.25)
    p.remove_all_lights()
    p.add_light(pv.Light(position=(-300, -500, 450), focal_point=(0, 0, 0), intensity=0.9))
    p.add_light(pv.Light(position=(400, -200, 100), focal_point=(0, 0, 0), intensity=0.35))
    p.add_light(pv.Light(light_type="headlight", intensity=0.3))
    p.camera_position = camera
    p.camera.zoom(zoom)
    p.screenshot(path)
    p.close()


def main():
    basket = ab.build_basket()
    one = [(mesh(basket), PLASTIC, 1.0)]
    c = (0, -ab.DEPTH / 2, ab.HEIGHT / 2)
    shot(one, OUT / "preview_angle.png", [(-220, -330, 330), c, (0, 0, 1)])
    shot(one, OUT / "preview_back.png", [(200, 320, 260), c, (0, 0, 1)])

    # two baskets side by side along the end wall, each on its pair of hooks
    step = ab.LENGTH + ab.BETWEEN
    scene = []
    for i in range(ab.COUNT):
        x = (i - (ab.COUNT - 1) / 2) * step
        scene.append((mesh(Pos(x, 0, 0) * basket), PLASTIC, 1.0))
        scene += [(mesh(ab.build_hook(x + hx)), HOOK, 1.0) for hx in ab.HOOK_XS]
    lip_z = ab.HEIGHT - ab.RIM_ABOVE_LIP
    shot(scene + tank_end(lip_z), OUT / "preview_in_tank.png",
         [(-260, -520, 330), (0, -40, 80), (0, 0, 1)], size=(1100, 850))
    print("rendered previews to", OUT)


if __name__ == "__main__":
    main()
