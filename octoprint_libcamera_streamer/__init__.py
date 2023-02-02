import logging
import logging.handlers
from typing import Union

import flask
import octoprint.plugin

from octoprint_libcamera_streamer.install import LibcameraInstaller


class LibcameraStreamerPlugin(octoprint.plugin.SettingsPlugin,
                              octoprint.plugin.AssetPlugin,
                              octoprint.plugin.TemplatePlugin,
                              octoprint.plugin.SimpleApiPlugin,
                              ):
    def __init__(self):
        super().__init__()
        self._console_logger = logging.getLogger("octoprint.plugins.libcamera_streamer.console")

        self.installer = LibcameraInstaller(self)

    def initialize(self):
        console_logging_handler = logging.handlers.RotatingFileHandler(
            self._settings.get_plugin_logfile_path(postfix="console"),
            maxBytes=2 * 1024 * 1024,
            encoding="utf-8",
        )
        console_logging_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
        console_logging_handler.setLevel(logging.DEBUG)

        self._console_logger.addHandler(console_logging_handler)
        self._console_logger.setLevel(logging.DEBUG)
        self._console_logger.propagate = False

        # Add websocket message printer so I can see what's going on
        def msg_receiver(plugin, data, *args, **kwargs):
            if plugin != self._identifier:
                return

            self._logger.debug("[WEBSOCKET]: %s", data)

        self._plugin_manager.register_message_receiver(msg_receiver)

    def send_ui_message(self, msg_type, content):
        self._plugin_manager.send_plugin_message(self._identifier, {
            "type": msg_type,
            "content": content
        })

    def send_log_entry(self, level: int, message: str):
        self.send_ui_message("log", {
            "level": level,
            "message": message
        })

    def dual_log(self, level: int, message: Union[str, list]):
        if isinstance(message, tuple):
            for line in message:
                self._console_logger.log(level, line)
        else:
            self._console_logger.log(level, message)

        self.send_log_entry(level, message)

    def on_api_get(self, request):
        result = {
            "error": ""
        }

        missing = self.installer.get_missing_packages()
        result["missing"] = missing
        if missing is None:
            result["error"] += "Unable to fetch missing packages"

        downloaded = self.installer.camera_streamer_path.exists()
        result["downloaded"] = downloaded

        installed = self.installer.camera_streamer_bin.exists()
        result["installed"] = installed

        return flask.jsonify(result)

    def on_api_command(self, command, data):
        if command == "install_dependencies":
            # TODO run async
            password = data.get("password", "")
            self.installer.command_install_dependencies(password)
        elif command == "install_streamer":
            # TODO run async
            password = data.get("password", "")
            self.installer.command_install_streamer(password)
        elif command == "download":
            # TODO run async
            overwrite = data.get("overwrite", False)
            self.installer.command_download_streamer(overwrite)

    def get_api_commands(self):
        return {
            "install_dependencies": ["password"],
            "install_streamer": ["password"],
            "download": []
        }

    def get_settings_defaults(self):
        return {}

    def get_assets(self):
        return {
            "js": ["js/libcamera_streamer.js"],
            "css": ["css/libcamera_streamer.css"],
        }

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "libcamera_streamer": {
                "displayName": "Libcamera Streamer",
                "displayVersion": self._plugin_version,
                "type": "github_release",
                "user": "cp2004",
                "repo": "OctoPrint-LibcameraStreamer",
                "current": self._plugin_version,
                # update method: pip
                "pip": "https://github.com/cp2004/OctoPrint-LibcameraStreamer/archive/{target_version}.zip",
            }
        }


__plugin_name__ = "Libcamera Streamer"
__plugin_pythoncompat__ = ">=3.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = LibcameraStreamerPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
