import os
from typing import Union
import logging
import pathlib
import shutil

from octoprint.util.commandline import CommandlineCaller, CommandlineError
from flask import abort

from octoprint_libcamera_streamer.util import get_package_list


LIBCAMERA_REQUIREMENTS = [
    "libavformat-dev",
    "libcamera-dev",
    "liblivemedia-dev",
    "libjpeg-dev",
    "cmake",
    "libboost-program-options-dev",
    "libdrm-dev",
    "libexif-dev",
]


def get_environment():
    env = os.environ.copy()
    # Avoid prompt errors
    env["DEBIAN_FRONTEND"] = "noninteractive"
    return env


class LibcameraInstaller:
    def __init__(self, plugin):
        self.logger = logging.getLogger("octoprint.plugins.libcamera_streamer.installer")
        self.plugin = plugin

        self.camera_streamer_path = pathlib.Path.home() / "camera-streamer"
        self.camera_streamer_bin = pathlib.Path("/usr/local/bin/camera-streamer")

        def on_log_call(*lines):
            self.plugin.dual_log(logging.WARNING, lines)  # Warning is abused for the caller

        def on_log_stdout(*lines):
            self.plugin.dual_log(logging.INFO, lines)

        def on_log_stderr(*lines):
            self.plugin.dual_log(logging.ERROR, lines)

        self.command_line = CommandlineCaller()
        self.command_line.on_log_call = on_log_call
        self.command_line.on_log_stdout = on_log_stdout
        self.command_line.on_log_stderr = on_log_stderr

    def get_missing_packages(self) -> Union[list, None]:
        # this should be fast as it is called in sync on the API
        # Currently it can be a bit slow (0.5s)
        # TODO maybe look into caching the result?
        missing = []
        try:
            installed_packages = get_package_list()
        except CommandlineError as err:
            self.logger.error("Unable to get package list: %s", err)
            return None

        for package in LIBCAMERA_REQUIREMENTS:
            if package not in installed_packages:
                missing.append(package)

        self.logger.debug("Identified missing packages: (%s)", ", ".join(missing))

        return missing

    def command_install_dependencies(self, sudo_password: str = "") -> Union[tuple, None]:
        missing = self.get_missing_packages()
        if missing is None:
            # Error, don't proceed
            return

        for package in missing:
            self.logger.info("Installing package %s", package)
            try:
                self.command_line.call(
                    ["sudo", "-S", "apt-get", "install", "-y", package], input=sudo_password, env=get_environment()
                )
            except CommandlineError as err:
                self.logger.error("Unable to install package %s: %s", package, err)
                return err.returncode, package

    def command_download_streamer(self, overwrite: bool = False):
        if self.camera_streamer_path.exists():
            self.logger.warning("Camera streamer appears to already exist at %s", self.camera_streamer_path)
            if overwrite:
                self.logger.warning("Overwriting existing camera streamer")
                shutil.rmtree(self.camera_streamer_path)
            else:
                # TODO error the API
                return

        self.logger.info("Downloading camera streamer to %s", self.camera_streamer_path)

        try:
            self.command_line.call(["git", "clone", "https://github.com/ayufan/camera-streamer.git", str(self.camera_streamer_path)], "--depth", "1")
        except CommandlineError as err:
            self.logger.exception("Unable to download camera streamer: %s", err)
            # TODO error the API
            return

    def command_install_streamer(self, sudo_password: str = ""):
        # Prerequisite checks for deps & source download
        missing_deps = self.get_missing_packages()
        if missing_deps is None:
            # TODO error the API
            return

        if len(missing_deps) > 0:
            self.logger.error("Unable to install camera streamer, missing dependencies: %s", ", ".join(missing_deps))
            # TODO error the API
            return

        if not self.camera_streamer_path.exists():
            self.logger.error("Unable to install camera streamer, it does not exist at %s", self.camera_streamer_path)
            # TODO error the API
            return

        # Build the streamer
        self.logger.info("Building camera streamer")
        try:
            self.command_line.call(
                ["make"],
                cwd=str(self.camera_streamer_path),
            )
        except CommandlineError as err:
            self.logger.error("Unable to build camera streamer: %s", err)
            # TODO error the API
            return

        try:
            self.command_line.call(
                ["sudo", "-S", "make", "install"],
                cwd=str(self.camera_streamer_path),
                input=sudo_password,
            )
        except CommandlineError as err:
            self.logger.error("Unable to install camera streamer: %s", err)
            # TODO error the API
            return

    def command_uninstall_streamer(self, sudo_password: str = ""):
        # TODO is a way to remove the streamer necessary?
        pass
