"""Linter module"""

import logging
import os
import threading
import sublime  # pylint: disable=import-error
import sublime_plugin  # pylint: disable=import-error
from .linter import Marker


logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


def load_settings(key):
    s = sublime.load_settings("Pytools.sublime-settings")
    return s.get(key)


def get_sysenv():
    new_paths = load_settings("path")
    env = os.environ.copy()
    env["PATH"] = new_paths + os.path.pathsep + env["PATH"]
    return env


MARKER = None   # type: Marker
LOADED = False

def plugin_loaded():
    global MARKER
    global LOADED
    MARKER = Marker()
    LOADED = True


class PytoolsLintCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if LOADED:
            thread = threading.Thread(target=self.lint)
            thread.start()

    def lint(self):
        view = self.view
        env = get_sysenv()
        # logger.debug(env)
        MARKER.lint(view, env)


class Linter(sublime_plugin.EventListener):
    def on_hover(self, view, point, hover_zone):
        if hover_zone == sublime.HOVER_GUTTER:
            MARKER.get_message(view, point)

    def on_post_save_async(self, view):
        MARKER.clear_view(view)
        pass
