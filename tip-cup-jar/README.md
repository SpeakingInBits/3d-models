# Tip Cup Jar

A coffee-cup tip jar with a screw-on lid, a 50 × 10 mm money slot for coins and folded bills,
and recessed spots for stickers.

| Assembled | Exploded |
|---|---|
| ![Tip cup jar](out/preview_angle.png) | ![Exploded view](out/preview_exploded.png) |

## Files to print

Both parts print without supports. Designed for a Prusa MK4 printing PETG (not yet test-printed).

| File | Notes |
|---|---|
| [out/cup.stl](out/cup.stl) | 88 mm wide, 102 mm tall. Print upright. |
| [out/lid.stl](out/lid.stl) | Already flipped top-down for printing. |

The assembled jar is about 143 mm tall. A STEP assembly for other CAD tools is in
[out/tip_cup_assembly.step](out/tip_cup_assembly.step).

Print tips: set the seam to *Rear* or *Aligned* so the threads turn smoothly.

## Stickers

The recesses are portrait, shaped like a phone photo held upright. Every recess is 1.5 mm deep
with 4 mm corner radii, and stickers are 1 mm smaller all round with 3 mm rounded corners. With
the default settings:

| Part | Spots | Recess | Sticker |
|---|---|---|---|
| Cup | 8 (4 around, 2 rows) | 27 × 36 mm | **25 × 34 mm** |
| Lid | 4 | 24 × 32 mm | **22 × 30 mm** |

### Changing the spots

Set these at the top of [tip_cup.py](tip_cup.py):

| Parameter | Default | What it does |
|---|---|---|
| `CUP_SPOT_COLUMNS` | 4 | Spots around the cup |
| `CUP_SPOT_ROWS` | 2 | Rows of spots on the cup |
| `LID_SPOTS` | 4 | Spots around the lid. They line up with the cup's columns when the counts match. |
| `SPOT_ASPECT` | 4/3 | Height ÷ width. Use 16/9 for screenshot-shaped spots. |
| `SPOT_GAP` | 4 | Minimum space between neighbouring spots, across and between rows |
| `CUP_SPOT_MARGIN` | 5 | Space kept clear at the base of the cup and below the shoulder |
| `LID_SPOT_MARGIN` | 3 | Space kept clear at the bottom and top of the lid's sloped face |
| `SAME_SPOT_SIZE` | False | True shrinks the larger set of spots so the cup and lid take one sticker size |
| `SPOT_START_ANGLE` | 45 | Angle of the first column. 270 centres a spot on the front. |

The cup and lid spots are each sized automatically to the largest whole-millimetre size that
fits, so adding spots makes them smaller and shrinking the gap or margins makes them bigger.
The script prints the spot and sticker sizes when it runs. Set a count to 0 for no spots on
that part.

### Photoshop templates (Cricut Print Then Cut)

[stickers/sticker_template.jsx](stickers/sticker_template.jsx) builds one Photoshop template
per sticker size: `sticker_cup.psd` and `sticker_lid.psd`, at 300 DPI with no bleed or
margins. Run it in Photoshop with **File > Scripts > Browse** and it saves them next to itself.
When the sticker sizes change, put the sizes that `tip_cup.py` prints into `STICKERS` at the
top of the script and run it again.

The **Sticker** group in each template is masked to the rounded corners, so anything you put in
it is trimmed to the sticker shape.

1. Open the PSD. With the *Your design* layer selected, use **File > Place Embedded** so the
   artwork lands inside the group.
2. **File > Export > Export As**, PNG with transparency on. Save one PNG per sticker.
3. In Cricut Design Space, upload the PNG as a **Print Then Cut** image. The transparent
   corners become the cut line.
4. On the canvas, lock the proportions and set the width to the sticker width (**25 mm** for
   the cup and **22 mm** for the lid with the default settings), then print and cut on sticker
   paper.

## Threads

2-start thread, so the lid goes on or off in about one turn. 45° flanks print cleanly in any
orientation. Clearance is 0.4 mm radial and 0.35 mm axial per flank (about 0.25 mm normal
to the flank), which is a slightly loose fit suited to PETG.

If the lid is too tight or loose on your printer, change `THREAD_AXIAL_GAP` (and if needed
`THREAD_CLEARANCE`) in [tip_cup.py](tip_cup.py) and reprint the lid.

## Customising

Every dimension is a parameter at the top of [tip_cup.py](tip_cup.py): cup height and taper,
sticker spot counts, shape and spacing, slot size and thread fit. Rebuild and re-render from the
repo root:

```bash
.venv/Scripts/python tip-cup-jar/tip_cup.py
.venv/Scripts/python tip-cup-jar/render.py
```
