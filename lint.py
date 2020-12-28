"""Linter module"""

import html
import logging
import os
import threading
import sublime  # pylint: disable=import-error
import sublime_plugin  # pylint: disable=import-error
from . import diagnostic


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
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


ERROR = 1
WARNING = 2
INFORMATION = 3
HINT = 4


MARKER = None


class Marker:
    """Marker object

    Severity level
    * ERROR
    * WARNING
    * INFORMATION
    * HINT
    """

    mark_key = "marker%s%s"

    @staticmethod
    def get_scope(severity):
        """get scope follow severity"""
        scope = {
            ERROR: "Invalid",
            WARNING: "Invalid",
            INFORMATION: "Comment",
            HINT: "Comment",
        }
        return scope[severity]

    @staticmethod
    def get_flags(severity):
        """get flag follow severity"""

        flags = {
            ERROR: sublime.DRAW_NO_OUTLINE,
            WARNING: sublime.DRAW_NO_FILL
            | sublime.DRAW_NO_OUTLINE
            | sublime.DRAW_SOLID_UNDERLINE,
            INFORMATION: sublime.DRAW_NO_FILL
            | sublime.DRAW_NO_OUTLINE
            | sublime.DRAW_SQUIGGLY_UNDERLINE
            | sublime.HIDE_ON_MINIMAP,
            HINT: sublime.DRAW_NO_FILL
            | sublime.DRAW_NO_OUTLINE
            | sublime.DRAW_SQUIGGLY_UNDERLINE
            | sublime.HIDE_ON_MINIMAP,
        }
        return flags[severity]

    @staticmethod
    def get_icon(severity):
        """get icon follow severity"""

        icon = {ERROR: "circle", WARNING: "dot", INFORMATION: "dot", HINT: "bookmark"}
        return icon[severity]

    @staticmethod
    def add_regions(view, key, regions, scope, icon, flags):
        view.add_regions(
            key=key,
            regions=regions,
            scope=scope,
            icon=icon,
            flags=flags,
        )

    def __init__(self):
        self.marks = {}  # {view_id: {line: {"regions":None,"diagnostic message":""}}}

    @staticmethod
    def prioritized(now, cached):
        return True if now < cached else False

    def set_marker(self, view, severity, line, column, message, message_id):
        view_id = view.id()
        region = view.word(view.text_point(line, column))
        message = "%s: %s" % (message_id, message)

        if self.marks.get(view_id) is None:
            self.marks[view_id] = {}

        try:
            cached = self.marks[view_id][line]["severity"]
        except KeyError:
            cached = 4

        if Marker.prioritized(severity, cached):
            self.marks[view_id][line] = {
                "region": region,
                "message": message,
                "severity": severity,
            }
            # logger.debug(self.marks[view_id])

    def apply(self, view):
        logger.debug(self.marks)
        view_id = view.id()
        marks_err = list(
            filter(lambda mark: mark["severity"] == ERROR, self.marks[view_id].values())
        )
        marks_warn = list(
            filter(lambda mark: mark["severity"] == WARNING, self.marks[view_id].values())
        )
        marks_info = list(
            filter(lambda mark: mark["severity"] == INFORMATION, self.marks[view_id].values())
        )
        marks_hint = list(
            filter(lambda mark: mark["severity"] == HINT, self.marks[view_id].values())
        )
        # logger.debug(marks_info)
        err_regions = [mark["region"] for mark in marks_err]
        warn_regions = [mark["region"] for mark in marks_warn]
        info_regions = [mark["region"] for mark in marks_info]
        hint_regions = [mark["region"] for mark in marks_hint]

        region_map = {
            ERROR: err_regions,
            WARNING: warn_regions,
            INFORMATION: info_regions,
            HINT: hint_regions,
        }

        for severity in region_map:
            scope = Marker.get_scope(severity)
            icon = Marker.get_icon(severity)
            flags = Marker.get_flags(severity)
            key = Marker.mark_key % (view.file_name(), severity)
            regions = region_map[severity]

            Marker.add_regions(view, key, regions, scope, icon, flags)

    def clear(self, view):
        for severity in (ERROR,WARNING,INFORMATION,HINT,):
            key = Marker.mark_key % (view.file_name(), severity)
            view.erase_region(key)

        del self.marks[view.id()]

    def get_message(self, view, line):
        try:
            region = view.line(line)
            marks = list(
                filter(lambda mark: region.contains(mark["region"].a), self.marks[view.id()].values())
            )
            return marks[0]["message"] if marks != [] else None
        except KeyError:
            return None


def plugin_loaded():
    global MARKER
    MARKER = Marker()


class PytoolsLintCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        thread = threading.Thread(target=self.lint)
        thread.start()

    def lint(self):
        view = self.view
        env = get_sysenv()

        file_name = view.file_name()
        file_path = os.path.abspath(file_name)

        lint = diagnostic.Pylint(file_path, env=env)
        result_msg = lint.lint(template=diagnostic.PylintFormatter.template)
        formatted_messages = diagnostic.PylintFormatter.parse_output(result_msg)

        for msg in formatted_messages:
            severity = msg["severity"]
            line = msg["line"] - 1
            column = msg["column"]
            message = msg["message"]
            message_code = msg["code"]
            MARKER.set_marker(view, severity, line, column, message, message_code)

        MARKER.apply(view)


class Linter(sublime_plugin.EventListener):
    def on_hover(self, view, point, hover_zone):
        if hover_zone == sublime.HOVER_GUTTER:
            self.get_message(view, point)

    def get_message(self, view, point):
        line, _ = view.rowcol(point)
        file_name = view.file_name()
        msg = MARKER.get_message(view, line)
        # logger.debug(msg)
#         if msg is not None:
#             msg = html.escape(msg, quote=False)
#             content = "%s" % (msg)
#             self.show_popup(view, content, point)

#     def show_popup(self, view, content, location):
#         if content is not None:
#             view.show_popup(
#                 content,
#                 sublime.HIDE_ON_MOUSE_MOVE_AWAY,
#                 location=location,
#                 max_width=900,
#                 on_navigate=None,
#             )

#     def on_post_save_async(self, view):
#         MARKER.clear(view)

