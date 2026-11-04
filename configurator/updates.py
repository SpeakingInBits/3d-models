"""Keeps an installed copy of the app up to date from the project's GitHub releases, with Velopack.

The Release workflow publishes the package and its release list (releases.win-x64.json) there. When
the app is run from source it isn't installed, so everything here does nothing.
"""

import os
import threading

import velopack

# "latest/download" always serves the newest release's files. Asking GitHub's API instead would be
# limited to 60 requests an hour per IP address.
RELEASE_FILES = "https://github.com/SpeakingInBits/3d-models/releases/latest/download/"


def run_install_hooks():
    """Must run first: the installer starts the app to set it up, and this exits straight after."""
    velopack.App().run()


class Updater:
    def __init__(self):
        self.update = None  # set once a newer version has finished downloading
        try:
            # CONFIGURATOR_UPDATE_SOURCE, a folder of packaged releases, tries out an update first
            source = os.environ.get("CONFIGURATOR_UPDATE_SOURCE") or RELEASE_FILES
            self.manager = velopack.UpdateManager(source)
        except Exception:  # not installed
            self.manager = None

    @property
    def version(self):
        return self.manager.get_current_version() if self.manager else None

    @property
    def new_version(self):
        return self.update.TargetFullRelease.Version if self.update else None

    def check_in_background(self):
        if self.manager:
            threading.Thread(target=self.download, daemon=True).start()

    def download(self):
        try:
            update = self.manager.check_for_updates()
            if update:
                self.manager.download_updates(update)
                self.update = update
        except Exception as error:  # usually offline; the app checks again next time it opens
            print(f"Update check failed: {error}")

    def restart(self):
        """Closes the app, installs the downloaded update and opens the new version."""
        self.manager.apply_updates_and_restart(self.update)
