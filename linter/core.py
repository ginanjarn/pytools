"""core linter module"""


import logging
import os
import sublime  # pylint: disable=import-error
from .tools import pylint as pylint # type: ignore

try:
    # required for typing inspection
    from typing import List, Iterator, Optional, Dict, Any
except ImportError:
    ...

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


ERROR = 1
WARNING = 2
INFORMATION = 3
HINT = 4


def get_flags(severity: int) -> int:
    flags = {
        ERROR: sublime.DRAW_NO_OUTLINE,
        WARNING: sublime.DRAW_NO_FILL
        | sublime.DRAW_NO_OUTLINE
        | sublime.DRAW_SOLID_UNDERLINE,
        INFORMATION: sublime.DRAW_NO_FILL
        | sublime.DRAW_NO_OUTLINE
        | sublime.DRAW_SOLID_UNDERLINE
        | sublime.HIDE_ON_MINIMAP,
        HINT: sublime.DRAW_NO_FILL
        | sublime.DRAW_NO_OUTLINE
        | sublime.DRAW_SQUIGGLY_UNDERLINE
        | sublime.HIDE_ON_MINIMAP,
    }
    return flags[severity]


def get_scope(severity: int) -> str:
    scope = {
        ERROR: "Invalid",
        WARNING: "Invalid",
        INFORMATION: "Comment",
        HINT: "Comment",
    }
    return scope[severity]


def get_icon(severity: int) -> str:
    icon = {ERROR: "circle", WARNING: "dot", INFORMATION: "bookmark", HINT: "bookmark"}
    return icon[severity]


class Mark:
    __slots__ = ["severity", "code", "module", "region", "column", "message"]

    def __init__(
        self,
        severity: int,
        code: str,
        module: str,
        region: sublime.Region,
        message: str,
    ) -> None:
        self.severity = severity
        self.code = code
        self.module = module
        self.region = region
        self.message = message

    def __repr__(self) -> str:
        return (
            "[severity: {severity}, code: {code}, module: {module}, "
            "region: {region}, message: {message}]".format(
                severity=self.severity,
                code=self.code,
                module=self.module,
                region=self.region,
                message=self.message,
            )
        )


class ViewMark:
    __slots__ = ["view", "id_", "marks"]

    @staticmethod
    def add_regions(
        view: sublime.View,
        key: str,
        regions: "List[sublime.Region]",
        scope: str,
        icon: str,
        flags: int,
    ) -> None:
        view.add_regions(key, regions, scope, icon, flags)

    @staticmethod
    def show_popup(
        view: sublime.View,
        content: str,
        flags: int,
        location: int,
        max_width: int = 900,
    ) -> None:
        view.show_popup(content, flags, location, max_width)

    def __init__(self, view: sublime.View) -> None:
        self.view = view
        self.id_ = view.id()
        self.marks = []  # type: List[Mark]

    def make_region(self, line: int, column: int) -> sublime.Region:
        return self.view.word(self.view.text_point(line, column))

    def add_mark(
        self,
        severity: int,
        code: str,
        module: str,
        line: int,
        column: int,
        message: str,
    ) -> None:
        region = self.make_region(line - 1, column)  # sublime zero based line index
        mark = Mark(severity, code, module, region, message)
        # logger.debug(mark)
        self.marks.append(mark)

    def get_message(self, pos: "sublime.Point") -> "Optional[str]":
        region = self.view.line(pos)  # type : sublime.Region

        def match(mark: Mark):
            return region.contains(mark.region.a)

        matches = filter(match, self.marks)
        message = "\n".join(
            ["%s: %s" % (match.code, match.message) for match in matches]
        )  # type : str
        return message

    @staticmethod
    def format_html(source: str) -> str:
        lines = source.splitlines()
        return "".join(["<div>%s</div>" % (line) for line in lines])

    def apply(self):
        severities = [ERROR, WARNING, INFORMATION, HINT]

        for severity in severities:
            key = "%s:%s" % (self.id_, severity)
            scope = get_scope(severity)
            flags = get_flags(severity)
            icon = get_icon(severity)

            def filter_marks(marks: "List[Mark]", severity: int) -> "Iterator[Mark]":
                def match(mark: Mark) -> bool:
                    return mark.severity == severity

                return filter(match, marks)

            regions = [mark.region for mark in filter_marks(self.marks, severity)]
            ViewMark.add_regions(self.view, key, regions, scope, icon, flags)

    def clear_mark(self):
        severities = [ERROR, WARNING, INFORMATION, HINT]

        for severity in severities:
            key = "%s:%s" % (self.id_, severity)
            self.view.erase_regions(key)


class Marker:
    def __init__(self):
        self.marks = {}  # type : Dict[int, ViewMark]

    def lint(self, view: sublime.View, env: "Optional[Dict[str, Any]]" = None):
        file_name = str(view.file_name())
        module = os.path.abspath(file_name)
        messages = pylint.lint(module, env)
        id_ = view.id()

        if id_ not in self.marks:
            self.marks[id_] = ViewMark(view)

        for message in messages:
            # logger.debug(message)
            self.marks[id_].add_mark(
                message[0], message[1], message[2], message[3], message[4], message[5]
            )

        self.marks[id_].apply()

    def clear_view(self, view: sublime.View) -> None:
        id_ = view.id()
        if id_ in self.marks:
            self.marks[id_].clear_mark()
            del self.marks[view.id()]

    def get_message(self, view: sublime.View, pos: "sublime.Point") -> None:
        id_ = view.id()
        if id_ not in self.marks:
            return

        message = self.marks[id_].get_message(pos)
        # logger.debug(message)

        if message:  # for string
            formatted = ViewMark.format_html(message)
            # logger.debug(formatted)
            ViewMark.show_popup(
                view, formatted, flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY, location=pos
            )
