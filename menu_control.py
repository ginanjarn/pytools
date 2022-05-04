"""handle application menu command"""

import os

import sublime
import sublime_plugin

from .api import settings


class PytoolsEditSettingsCommand(sublime_plugin.ApplicationCommand):
    """edit settings"""

    def run(self):
        sublime.run_command("new_window")

        # open default settings
        package_path = os.path.dirname(__file__)
        file_name = os.path.join(package_path, settings.BASE_NAME)
        view = sublime.active_window().open_file(file_name)

        # set window to current active view window
        window = view.window()

        # set layout to 2 column
        window.run_command(
            "set_layout",
            {
                "cols": [0.0, 0.5, 1.0],
                "rows": [0.0, 1.0],
                "cells": [[0, 0, 1, 1], [1, 0, 2, 1]],
            },
        )

        # open user settings
        file_name = os.path.join(sublime.packages_path(), "User", settings.BASE_NAME)
        window.open_file(file_name)
