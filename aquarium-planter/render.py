"""Render preview images of the planter, the hooks and the tray on a stand-in tank frame."""

import tempfile
from pathlib import Path

import pyvista as pv
from build123d import export_stl

import aquarium_planter as ap

OUT = Path(__file__).parent / "out"
PLASTIC, TRAY, FRAME, GLASS, WATER = "#ecebe6", "#d9d4cc", "#2b2d31", "#a9d4e0", "#4f8fb8"


def mesh(part):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "part.stl"
        export_stl(part, path)
        return pv.read(path)


def frame(x0, x1, lip_y, lip_z, side=1):
    """One long side of the tank's frame: the lip, the frame above it and the glass below.

    lip_y is the lip's edge and side is +1 if the tank wall is toward +Y, -1 toward -Y.
    """
    def span(a, b):
        a, b = lip_y + side * a, lip_y + side * b
        return min(a, b), max(a, b)

    lip = pv.Box(bounds=(x0, x1, *span(0, ap.LIP_W), lip_z - 4, lip_z))
    top = pv.Box(bounds=(x0, x1, *span(ap.LIP_W, ap.LIP_W + ap.FRAME_TOP_W),
                         lip_z - 30, lip_z + ap.LIP_DROP))
    glass = pv.Box(bounds=(x0, x1, *span(ap.LIP_W + 4, ap.LIP_W + 10), lip_z - 140, lip_z - 30))
    return [(lip + top, FRAME, 1.0), (glass, GLASS, 0.35)]


def water(x0, x1, y0, y1, z):
    return [(pv.Box(bounds=(x0, x1, y0, y1, z - 80, z)), WATER, 0.3)]


def shot(meshes, path, camera, size=(1000, 750), zoom=1.0, from_below=False):
    p = pv.Plotter(off_screen=True, window_size=size)
    p.set_background("#b9b9bd")
    for m, color, opacity in meshes:
        p.add_mesh(m, color=color, opacity=opacity, smooth_shading=True,
                   split_sharp_edges=True, feature_angle=25, specular=0.25)
    p.remove_all_lights()
    p.add_light(pv.Light(position=(-300, -500, 450), focal_point=(0, 0, 0), intensity=0.9))
    p.add_light(pv.Light(position=(400, -200, 100), focal_point=(0, 0, 0), intensity=0.35))
    p.add_light(pv.Light(light_type="headlight", intensity=0.3))
    if from_below:
        p.add_light(pv.Light(position=(-300, -400, -500), focal_point=(0, 0, 0), intensity=0.9))
    p.camera_position = camera
    p.camera.zoom(zoom)
    p.screenshot(path)
    p.close()


def main():
    planter = ap.build_planter()
    pm = mesh(planter)
    c = ((ap.BASKET_X1 - ap.CUP_R) / 2, -35, 30)
    shot([(pm, PLASTIC, 1.0)], OUT / "preview_angle.png", [(-150, -330, 260), c, (0, 0, 1)])
    shot([(pm, PLASTIC, 1.0)], OUT / "preview_bottom.png", [(-100, -250, -320), c, (0, 0, 1)])

    # hanging from the hooks on the back wall of the tank
    lip_z = ap.HEIGHT - ap.RIM_ABOVE_LIP
    hooks = [(mesh(ap.build_hook(x)), "#f2c14e", 1.0) for x in ap.HOOK_XS]
    x0, x1 = -ap.CUP_R - 40, ap.BASKET_X1 + 40
    tank = frame(x0, x1, ap.BACK_GAP, lip_z) + water(x0, x1, -120, ap.BACK_GAP + ap.LIP_W + 4,
                                                     lip_z - 22)
    scene = [(pm, PLASTIC, 1.0)] + hooks + tank
    shot(scene, OUT / "preview_hooks.png", [(-140, -330, 250), (c[0], -20, 40), (0, 0, 1)])
    # cut through the first hook to show how it sits on the lip and wraps over the frame
    hx = ap.HOOK_XS[0]
    cut = [(m.clip(normal="-x", origin=(hx, 0, 0)), color, 1.0)
           for m, color, _ in [(pm, PLASTIC, 1.0)] + hooks + tank[:1]]
    shot(cut, OUT / "preview_hook_section.png",
         [(hx - 300, 14, lip_z - 2), (hx, 14, lip_z - 2), (0, 0, 1)], size=(900, 600), zoom=2.6)

    # the tray across the tank, front lip to back lip
    parts, keys = ap.tray_assembly()
    half_a, half_b, p1, p2 = [mesh(p) for p in parts]
    x0, x1 = -ap.TRAY_W / 2 - 60, ap.TRAY_W / 2 + 60
    tank = frame(x0, x1, ap.OPENING / 2, 0, 1) + frame(x0, x1, -ap.OPENING / 2, 0, -1)
    tank += water(x0, x1, -ap.OPENING / 2 - ap.LIP_W - 4, ap.OPENING / 2 + ap.LIP_W + 4, -22)
    scene = [(half_a, TRAY, 1.0), (half_b, TRAY, 1.0), (p1, PLASTIC, 1.0), (p2, PLASTIC, 1.0)]
    shot(scene + tank, OUT / "preview_tray.png", [(-380, -420, 380), (0, 0, -10), (0, 0, 1)],
         size=(1000, 800))
    under = [(half_a, TRAY, 1.0), (half_b, TRAY, 1.0)] + [(mesh(k), "#f2c14e", 1.0) for k in keys]
    shot(under, OUT / "preview_tray_bottom.png", [(-250, -330, -330), (0, 0, 0), (0, 0, 1)],
         size=(1000, 800), from_below=True)
    print("rendered previews to", OUT)


if __name__ == "__main__":
    main()
