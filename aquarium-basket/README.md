# Aquarium Basket

A grid-walled plant basket, like a dishwasher's cutlery basket, that hangs inside the tank against
its end wall. It's 5.5 in (140 mm) tall and 3.5 in (89 mm) out from the wall. Its length is worked
out so two of them fill the end wall side by side, with room to spare at the corners.

Each basket hangs from two clip-on hooks. The hooks drop over its back wall, sit on the frame's
inner lip and wrap over the top of the frame. The rim ends up level with the lip.

| Basket | Two on the end wall | Back (solid under the hooks) |
|---|---|---|
| ![Basket](out/preview_angle.png) | ![In the tank](out/preview_in_tank.png) | ![Back](out/preview_back.png) |

## Files to print

Designed for a Prusa MK4 printing PETG (not yet test-printed). PETG is fine in fresh water. Skip
any additives or colourants you wouldn't put in a tank. Both files are laid out the way they print,
and neither needs slicer supports.

| File | Print | Notes |
|---|---|---|
| [out/hook.stl](out/hook.stl) | 4 | Two per basket. The same file as the [planter's hook](../aquarium-planter/), so either works. |
| [out/basket.stl](out/basket.stl) | 2 | 135.5 × 88.9 mm, 139.7 mm tall. Prints open top up. |

Printing notes:
- The wall openings are about 8 mm square. Their tops are short flat bridges.
- The floor has 6 mm openings, small enough to hold gravel or clay pebbles.
- Solid bands run around the rim, the bottom and either side of each corner for stiffness.

A STEP file for other CAD tools is in [out/aquarium_basket.step](out/aquarium_basket.step).

## Fit

The tank's end wall is 287 mm between the front and back lip edges. Two baskets of 135.5 mm leave
6 mm at each end and 4 mm between them. They have to stay inside the lip edges, because the rim is
level with the lips and would hit the front and back lips at the corners.

The hooks are sized for this tank's frame. The lip is 8.5 mm below the top edge and 10 mm wide,
and the frame top is 14.3 mm (9/16 in) across. If you've already printed hooks for the planter,
they fit these baskets too.

About 115 mm of each basket sits under water when the water is 25 mm below the lip.

## Customising

Every dimension is a parameter at the top of [aquarium_basket.py](aquarium_basket.py). The ones
you're most likely to change:

| Parameter | Default | What it does |
|---|---|---|
| `HEIGHT`, `DEPTH` | 139.7, 88.9 | Basket height and how far it reaches out from the wall. |
| `COUNT` | 2 | How many baskets share the wall. The length adjusts to fit. |
| `END_CLEAR`, `BETWEEN` | 6, 4 | Room at the corners and between baskets. |
| `GRID_OPENING`, `FLOOR_OPENING` | 8, 6 | Size of the square openings in the walls and floor. |
| `OPENING` | 287 | The end wall's length between the lip edges. |

Rebuild and re-render from the repo root:

```bash
.venv/Scripts/python aquarium-basket/aquarium_basket.py
```

```bash
.venv/Scripts/python aquarium-basket/render.py
```
