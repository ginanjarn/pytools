"""Linter module"""

import html
import logging
import os
import threading
import sublime  # pylint: disable=import-error
import sublime_plugin  # pylint: disable=import-error
from . import diagnostic


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
    def get_flag(severity):
        """get flag follow severity"""

        flag = {
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
        return flag[severity]

    @staticmethod
    def get_icon(severity):
        """get icon follow severity"""

        icon = {ERROR: "circle", WARNING: "dot", INFORMATION: "dot", HINT: "bookmark"}
        return icon[severity]

    def __init__(self):
        self.marks = {}

    def is_prioritized(self, file_name, line, severity) -> bool:
        """check if more prioritized than cached"""

        cached = self.marks.get(Marker.mark_key % (file_name, line))
        prioritized = False
        if cached is not None:
            prioritized = cached["severity"] > severity
        else:
            prioritized = True
        return prioritized

    def add_mark(self, file_name, line, column, severity, message, **kwargs):
        """add mark

        Args:
            file_name(str)
            line(int): zero based indexed line
            column(int): zero based indexed column
            severity: severity level
            **kwargs: additional mapped data
        """

        line -= 1  # sublime use zero(0) based line index
        if self.is_prioritized(file_name, line, severity):
            key = Marker.mark_key % (file_name, line)
            self.marks[key] = {
                "file_name": file_name,
                "line": line,
                "column": column,
                "severity": severity,
                "message": message,
            }
            self.marks[key].update(kwargs)

    def add_regions(self, view, scope, regions, severity):
        key = "%s%s" % (view.file_name(), severity)
        view.add_regions(
            key=key,
            regions=regions,
            scope=scope,
            icon=Marker.get_icon(severity),
            flags=Marker.get_flag(severity),
        )

    def mark_error(self, view, regions):
        self.add_regions(view, "invalid", regions, ERROR)

    def mark_warning(self, view, regions):
        self.add_regions(view, "invalid", regions, WARNING)

    def mark_information(self, view, regions):
        self.add_regions(view, "comment", regions, INFORMATION)

    def mark_hint(self, view, regions):
        self.add_regions(view, "comment", regions, HINT)

    def get_region(self, view, line, column):
        return view.line(view.text_point(line, column))

    def apply(self, view):
        err_regs, warn_regs, info_regs, hint_regs = [], [], [], []

        def match(marks, file_name, severity):
            return (marks["file_name"] == file_name) and (marks["severity"] == severity)

        file_name = view.file_name()
        messages = filter(
            lambda mark: match(mark, file_name, ERROR), self.marks.values()
        )
        err_regs = [
            self.get_region(view, msg["line"], msg["column"]) for msg in messages
        ]
        self.mark_error(view, err_regs)

        messages = filter(
            lambda mark: match(mark, file_name, WARNING), self.marks.values()
        )
        warn_regs = [
            self.get_region(view, msg["line"], msg["column"]) for msg in messages
        ]
        self.mark_warning(view, warn_regs)

        messages = filter(
            lambda mark: match(mark, file_name, INFORMATION), self.marks.values()
        )
        info_regs = [
            self.get_region(view, msg["line"], msg["column"]) for msg in messages
        ]
        self.mark_information(view, info_regs)

        messages = filter(
            lambda mark: match(mark, file_name, HINT), self.marks.values()
        )
        hint_regs = [
            self.get_region(view, msg["line"], msg["column"]) for msg in messages
        ]
        self.mark_hint(view, hint_regs)

    def get_message(self, file_name, line):
        key = Marker.mark_key % (file_name, line)
        # logger.debug(key)
        mark = self.marks.get(key)
        message = None
        if mark is not None:
            message = "%s: %s" % (mark["msg_code"], mark["message"])
        # logger.debug(message)
        return message

    def clear(self, view, severity="all"):

        file_name = view.file_name()
        severity = (
            [ERROR, WARNING, INFORMATION, HINT] if severity == "all" else severity
        )

        def make_key(svt):
            return "%s%s" % (file_name, svt)

        keys = (make_key(svt) for svt in severity)

        for key in keys:
            view.erase_regions(key)

        def match(value, file_name):
            return value["file_name"] == file_name

        key_to_remove = [
            key for key, value in self.marks.items() if match(value, file_name)
        ]

        for key in key_to_remove:
            del self.marks[key]


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
            MARKER.add_mark(
                file_name,
                msg["line"],
                msg["column"],
                msg["severity"],
                msg["message"],
                msg_code=msg["code"],
            )

        MARKER.apply(view)


class Linter(sublime_plugin.EventListener):
    def on_hover(self, view, point, hover_zone):
        if hover_zone == sublime.HOVER_GUTTER:
            self.get_message(view, point)

    def get_message(self, view, point):
        line, _ = view.rowcol(point)
        file_name = view.file_name()
        msg = MARKER.get_message(file_name, line)
        # logger.debug(msg)
        if msg is not None:
            msg = html.escape(msg, quote=False)
            content = "%s" % (msg)
            self.show_popup(view, content, point)

    def show_popup(self, view, content, location):
        if content is not None:
            view.show_popup(
                content,
                sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                location=location,
                max_width=900,
                on_navigate=None,
            )

    def on_post_save_async(self, view):
        MARKER.clear(view)
