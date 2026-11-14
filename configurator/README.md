# Model Configurator

A desktop app for changing a model's parameters and building it, without editing its script.

Install it from the [latest release](https://github.com/SpeakingInBits/3d-models/releases/latest),
and it keeps itself up to date. Or start it from the repo root:

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

Each saved build goes in its own dated folder, along with a `parameters.json` listing what you
changed and a Photoshop template for each sticker size. Installed copies save to `Documents\3D Model Configurator`, and copies run from source save
to `custom-builds/`, which git ignores. The files in each model's `out` folder are not touched.

Your edits stay in place when you switch between models, until you close the app. **Reset to
defaults** puts the current model back to the values in its script.

## Making stickers

Models with sticker spots have a **Make stickers** button, which turns a photo into a sticker that
fits. The sizes come from the build in the picture, so they follow your changes. The button is
unavailable while that build is running or if it failed.

1. Pick which sticker you're making, if the model has more than one size.
2. Drop a photo on the window, or click **Open photo**. JPEG, PNG and iPhone HEIC photos all work.
3. Drag the photo to move it. Scroll or use the **Size** slider to resize it, and use the
   **Rotation** slider or **Rotate 90°** to turn it. The sticker is shown in full, with the rest of
   the photo faded around it. **Fill sticker** and **Show whole photo** centre it again.
4. Click **Export PNG**. Anywhere the photo doesn't cover stays white.

The PNG is the exact sticker size at 300 DPI, with transparent corners. Upload it to Cricut Design
Space as a **Print Then Cut** image and set its width to the size the app shows. Exports start in a
`stickers` folder next to your saved builds. Repeat for each sticker you want.

### Keeping the size of a printed model's stickers

Sticker sizes change with a model's parameters, so keep a file for anything you print. Every saved
build has a Photoshop template for each of its sticker sizes, such as `cup-25x34mm.psd`, next to its
STL files. For a default model, which has no saved build, click **Export Photoshop template** in the
sticker window. It works before you've added a photo.

The size stays in three places: the file's name, the name of the group inside it, and the document
itself, which opens at that size at 300 DPI. Exported PNGs have the size in their names too.

Design inside the **Sticker** group, which is masked to the sticker's rounded corners, then export a
PNG with transparency on and upload it to Cricut the same way.

## Speed

The app keeps a background worker running with the CAD libraries loaded, which uses about 450 MB of
memory. The first rebuild after opening waits for it to load, which takes about 5 seconds. After
that, the time is mostly the model's own geometry, roughly 2 seconds for the sticker stand, 3 for
the phone stand, 6 for the tip cup and 11 for the barista cup.

Previews are drawn on the CPU, so the app also works without OpenGL, such as on virtual machines
and remote desktops.

A change made during a rebuild waits for that rebuild to finish, then builds the latest values, and
**Save build** is unavailable until then. To skip the wait, turn on **Settings > Keep a spare
worker**. A second worker then stays loaded, so a change can replace the running rebuild at once,
for about 350 MB more memory. The setting is remembered in `settings.json` in the saved builds
folder.

Some parameters only make sense together, and not every combination builds. If a build fails, the
log shows the reason. A custom size can also need different stickers or a deeper base, so check
the sticker size in the log and each model's README.

## Releasing

Installed copies update themselves from GitHub Releases with [Velopack](https://velopack.io/). When
a new version is out, the app downloads it in the background and installs it the next time it
opens, or right away with **Restart now**. The window comes to the front when that button appears,
so it isn't missed behind other windows.

To publish a version, open **Actions > Release > Run workflow** on `main` and choose what's in it,
which picks the next version number. The workflow builds the package, checks that every model builds
with the packaged worker, and creates the release. Pull requests that change the app or its
packaging run the same build without releasing.

New and changed models reach installed copies with the next release, because they're bundled in the
package.

To build the package yourself, install the packaging requirements and
[vpk](https://docs.velopack.io/packaging/overview), then run this from the repo root:

```bash
.venv/Scripts/python -m pip install -r packaging/requirements.txt
```

```bash
dotnet tool install --global vpk --version 1.2.161
```

```bash
VERSION=1.2.3 PYTHON=.venv/Scripts/python bash packaging/package.sh
```

To try an update before publishing it, set `CONFIGURATOR_UPDATE_SOURCE` to a folder of packaged
releases before opening an installed copy.

## Adding a model

New models show up on their own. A model is any folder with a script that has a `main()` function
and an `OUT` constant. Every constant set to a plain value above the first function becomes a
parameter, grouped by the `# ---- section` comments, with its end-of-line comment as the note.

Numbers with a decimal point are treated as lengths in millimetres, and whole numbers as counts.
Names containing `ANGLE`, `TILT` or `OVERHANG` are degrees. Write a length as `10.0`, not `10`, or
it won't get an inch box.

To get the **Make stickers** button, have `main()` write `stickers.json` to `OUT`, and commit the
default model's copy. It's a list with an entry for each sticker size, with its `name`, `width`,
`height` and `corner` radius in millimetres and the `count` needed.
