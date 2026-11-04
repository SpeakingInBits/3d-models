# Model Configurator

A desktop app for changing a model's parameters and building it, without editing its script.

Start it from the repo root:

```bash
.venv/Scripts/python configurator/app.py
```

## Using it

1. Pick a model from the list.
2. Change any parameters. Lengths have a millimetre box and an inch box, and typing in either one
   updates the other.
3. Pause for a moment and the model rebuilds by itself. The log shows the finished size of each
   part in both units, and the picture changes to match.
4. Click **Save build** when you're happy, then **Open build folder** to get the STL files for your
   slicer.

Each saved build goes in its own dated folder under `custom-builds/`, which git ignores, along with
a `parameters.json` listing what you changed. The files in each model's `out` folder are not
touched.

Your edits stay in place when you switch between models, until you close the app. **Reset to
defaults** puts the current model back to the values in its script.

## Speed

The app keeps a background worker running with the CAD libraries loaded, which uses about 500 MB of
memory. The first rebuild after opening waits for it to load, which takes about 8 seconds. After
that, the time is mostly the model's own geometry, roughly 2 seconds for the sticker stand, 4 for
the phone stand, 8 for the tip cup and 14 for the barista cup.

A change made during a rebuild waits for that rebuild to finish, then builds the latest values, and
**Save build** is unavailable until then. To skip the wait, turn on **Settings > Keep a spare
worker**. A second worker then stays loaded, so a change can replace the running rebuild at once,
for about 450 MB more memory. The setting is remembered in `custom-builds/settings.json`.

Some parameters only make sense together, and not every combination builds. If a build fails, the
log shows the reason. A custom size can also need different stickers or a deeper base, so check
the sticker size in the log and each model's README.

## Adding a model

New models show up on their own. A model is any folder with a script that has a `main()` function
and an `OUT` constant. Every constant set to a plain value above the first function becomes a
parameter, grouped by the `# ---- section` comments, with its end-of-line comment as the note.

Numbers with a decimal point are treated as lengths in millimetres, and whole numbers as counts.
Names containing `ANGLE`, `TILT` or `OVERHANG` are degrees. Write a length as `10.0`, not `10`, or
it won't get an inch box.
