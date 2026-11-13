# 3D Models

Parametric, 3D-printable models written in Python with [build123d](https://github.com/gumyr/build123d).
Each model lives in its own folder with its source script, ready-to-print STLs and preview renders.

| Model | Description |
|---|---|
| [aquarium-planter](aquarium-planter/) | Planter with a perforated feeding cup and a slotted plant basket, on hooks or in a two-piece tray that rests on a framed tank's inner lip |
| [tip-cup-jar](tip-cup-jar/) | Coffee-cup tip jar with a screw-on coin-slot lid and recessed sticker spots |
| [barista-gift](barista-gift/) | Birthday tip cup for a barista with their name and two QR code billboards |
| [phone-stand](phone-stand/) | Charging stand for an iPhone 14 Pro Max on MagSafe with an Apple Watch charger pad |
| [sticker-stand](sticker-stand/) | Double-sided upside-down T desktop stand with four recessed sticker spots on each side |

## Setup

Requires Python 3.12 (Windows commands shown).

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

Then run a model's script from the repo root, for example:

```bash
.venv/Scripts/python tip-cup-jar/tip_cup.py
```

## Configurator

To change a model's parameters in millimetres or inches without editing its script, use the
[configurator](configurator/) app. Install it from the
[latest release](https://github.com/SpeakingInBits/3d-models/releases/latest), and it keeps itself up
to date. Or run it from source:

```bash
.venv/Scripts/python configurator/app.py
```
