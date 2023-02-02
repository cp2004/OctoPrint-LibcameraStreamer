import logging
from typing import Optional
import pathlib

from octoprint.util.commandline import CommandlineCaller, CommandlineError


package_requirements = [
    "libavformat-dev",
    "libcamera-dev",
    "liblivemedia-dev",
    "libjpeg-dev",
    "cmake",
    "libboost-program-options-dev",
    "libdrm-dev",
    "libexif-dev",
]


def get_package_list() -> list:
    caller = CommandlineCaller()
    _returncode, stdout, _stderr = caller.checked_call(["dpkg-query", "-f", "${Package}\n", "-W"])
    stdout = [line.strip() for line in stdout]

    return stdout


def missing_requirements() -> list:
    missing = []
    installed_packages = get_package_list()

    for package in package_requirements:
        if package not in installed_packages:
            missing.append(package)

    return missing


def download_camera_streamer():
    # git checkout camera-streamer to the user's home directory
    # first check that it's not already there
    path_to_cs = pathlib.Path.home() / "camera-streamer"

    if path_to_cs.exists():
        print("camera-streamer already exists")

    else:

        print("cloning camera-streamer")
        r, stdout, stderr = caller.call(["git", "clone", "https://github.com/ayufan/camera-streamer.git", str(path_to_cs)])

    # TODO check code
    print("making")
    r1, stdout1, stderr1 = caller.call(["make"], cwd=str(path_to_cs))

    sudo_password = input("pls provide sudo password: ")

    # TODO check code
    print("make installing")
    r2, stdout2, stderr2 = caller.call(["sudo", "-S", "make", "install"], cwd=str(path_to_cs), input=sudo_password)




if __name__ == "__main__":
    install_camerastreamer_requirements()
    print("done installing reqs")

    download_camera_streamer()
