#!/usr/bin/env bash
# Builds the configurator as a Windows program and packages it with Velopack, so installed copies
# can update themselves from the GitHub releases.
#
#   VERSION=1.2.3 packaging/package.sh
#
# Run from the repository root, with vpk (dotnet tool install -g vpk) on the PATH at the same version
# as velopack in requirements.txt. Set PYTHON if python isn't the one with the requirements installed.
# Writes to dist/:
#
#   ModelConfigurator-win-x64-Setup.exe       installer (installs for the current user, no admin needed)
#   ModelConfigurator-win-x64-Portable.zip    a folder that runs from anywhere and still updates
#   ModelConfigurator-<version>-win-x64-full.nupkg, releases.win-x64.json   what installed apps download to update
set -euo pipefail

version=${VERSION:?set VERSION, e.g. VERSION=1.2.3}
python=${PYTHON:-python}

rm -rf build
"$python" -m PyInstaller packaging/configurator.spec --distpath build/dist --workpath build/work --noconfirm
"$python" packaging/smoke_test.py build/dist/ModelConfigurator build/smoke

# No delta packages: each update downloads the whole app, which keeps the release simple.
vpk pack --packId ModelConfigurator --packTitle "3D Model Configurator" --packAuthors SpeakingInBits \
  --packVersion "$version" --channel win-x64 --runtime win-x64 --delta None --outputDir dist \
  --packDir build/dist/ModelConfigurator --mainExe ModelConfigurator.exe --icon packaging/app-icon/icon.ico
