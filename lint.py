import sublime
import sublime_plugin
import threading
import os
import subprocess
import re
import logging
from . import diagnostic
# import diagnostic


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter(
    '%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


def print_to_outputpane(msg):
    win = sublime.active_window()
    panel = win.create_output_panel("panel")
    panel.run_command("append", {"characters": msg})
    win.run_command('show_panel', {"panel": "output.panel"})


def hide_outputpane():
    win = sublime.active_window()
    win.run_command('hide_panel', {"panel": "output.panel"})


def load_settings(key):
    s = sublime.load_settings("Pytools.sublime-settings")
    return s.get(key)


def get_sysenv():
    new_paths = load_settings("path")
    env = os.environ.copy()
    env['PATH'] = new_paths + os.path.pathsep + env['PATH']
    return env


ERROR = 1
WARNING = 2
INFORMATION = 3
HINT = 4


class Marker:
    @staticmethod
    def get_flag(severity):
        flag = {
            ERROR: sublime.DRAW_NO_OUTLINE,
            WARNING: sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SOLID_UNDERLINE,
            INFORMATION: sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SOLID_UNDERLINE | sublime.HIDE_ON_MINIMAP,
            HINT: sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SOLID_UNDERLINE | sublime.HIDE_ON_MINIMAP,
        }
        return flag[severity]

    @staticmethod
    def get_icon(severity):
        icon = {
            ERROR: "circle",
            WARNING: "dot",
            INFORMATION: "dot",
            HINT: "bookmark"
        }
        return icon[severity]

    @staticmethod
    def set_selection(view, key, regions, severity):
        view.add_regions(key=key, regions=regions, scope="invalid",
                         icon=Marker.get_icon(severity), flags=Marker.get_flag(severity))

    def __init__(self, view):
        self.view = view
        file_name = view.file_name()
        self.mark = {
            "error": {"key": "%s_%s"%(file_name, ERROR), "regions": [], "severity": ERROR},
            "warning": {"key": "%s_%s"%(file_name, WARNING), "regions": [], "severity": WARNING},
            "information": {"key": "%s_%s"%(file_name, INFORMATION), "regions": [], "severity": INFORMATION},
            "hint": {"key": "%s_%s"%(file_name, HINT), "regions": [], "severity": HINT},
        }
        self.marked = {}

    def add_error(self, line, column):
        region = self.view.word(self.view.text_point(line, column))
        self.mark["error"]["regions"].append(region)

    def add_warning(self, line, column):
        region = self.view.word(self.view.text_point(line, column))
        self.mark["warning"]["regions"].append(region)

    def add_information(self, line, column):
        region = self.view.word(self.view.text_point(line, column))
        self.mark["information"]["regions"].append(region)

    def add_hint(self, line, column):
        region = self.view.word(self.view.text_point(line, column))
        self.mark["hint"]["regions"].append(region)

    def add(self, severity, line, column):

        # fit sublime zero(0) based line, from one(1) based pylint line
        line -= 1

        opt = {ERROR:self.add_error,WARNING:self.add_warning,
                INFORMATION:self.add_information,HINT:self.add_hint}
        
        opt[severity](line, column)

    def clean_mark(self):
        file_name = self.view.file_name()
        def keys(file_name, *args):
            return ["%s_%s"%(file_name, severity) for severity in args]
        
        for key in keys(file_name, ERROR, WARNING, INFORMATION, HINT):
            self.view.erase_regions(key)

        self.marked.clear()

    def apply(self):
        for mark in self.mark.values():
            Marker.set_selection(self.view, mark["key"],mark["regions"],mark["severity"])


class PylintCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        marker = Marker(self.view)
        marker.clean_mark()
        self.lint()

    def lint(self):
        view = self.view
        file_path = os.path.abspath(view.file_name())
        env = get_sysenv()
        lint = diagnostic.Pylint(file_path, env=env)
        result_msg = lint.lint(template=diagnostic.PylintFormatter.template)
        # logger.debug(result_msg)
        formatted_messages = diagnostic.PylintFormatter.parse_output(
            result_msg)

        marker = Marker(view)
        for msg in formatted_messages:
            logger.debug(msg)
            marker.add(msg["severity"],int(msg["line"]),int(msg["column"]))

        marker.apply()
