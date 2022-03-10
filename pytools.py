"""pythools implementation"""

import logging
import re
import os
import subprocess
from collections import defaultdict
from functools import wraps
from threading import Lock, Thread
from typing import Iterable, Iterator, List, Any, Optional, Dict

import sublime
import sublime_plugin

from .api import environment
from .api import client
from .api import settings

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
STREAM_HANDLER = logging.StreamHandler()
LOG_TEMPLATE = "%(levelname)s %(asctime)s %(filename)s:%(lineno)s  %(message)s"
STREAM_HANDLER.setFormatter(logging.Formatter(LOG_TEMPLATE))
LOGGER.addHandler(STREAM_HANDLER)

# prevent multiple request while in process
PROCESS_LOCK = Lock()


def pipe(func):
    """pipe command, only one request"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        while PROCESS_LOCK.locked():
            LOGGER.debug("busy")
            return None

        with PROCESS_LOCK:
            status_key = "pytools_status"
            view = sublime.active_window().active_view()
            try:
                view.set_status(status_key, "BUSY")
                return func(*args, **kwargs)
            finally:
                view.erase_status(status_key)

    return wrapper


# prevent multiple process running server
RUN_SERVER_LOCK = Lock()


def run_server_lock(func):
    """running server guard"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        while RUN_SERVER_LOCK.locked():
            return None
        with RUN_SERVER_LOCK:
            return func(*args, **kwargs)

    return wrapper


class PytoolsChangeInterpreterCommand(sublime_plugin.ApplicationCommand):
    """change python interpreter"""

    def run(self):
        LOGGER.info("PytoolsChangeInterpreterCommand")

        self.interpreters = list(set(environment.get_all_interpreter()))
        self.interpreters.sort(key=len)
        LOGGER.debug(self.interpreters)

        window: sublime.Window = sublime.active_window()
        current = settings.BASE_SETTING.get(settings.INTERPRETER)
        try:
            index = self.interpreters.index(current)
        except ValueError:
            index = 0
        window.show_quick_panel(
            self.interpreters,
            on_select=self.set_interpreter,
            flags=sublime.KEEP_OPEN_ON_FOCUS_LOST | sublime.MONOSPACE_FONT,
            selected_index=index,
        )

    def set_interpreter(self, index=-1):
        if index < 0:
            LOGGER.debug("nothing selected")
            return

        settings.BASE_SETTING.set(settings.INTERPRETER, self.interpreters[index])
        LOGGER.debug(f"selected: {self.interpreters[index]}")
        sublime.run_command("pytools_shutdown_server")


class PytoolsRunServerCommand(sublime_plugin.ApplicationCommand):
    """run server"""

    def run(self):
        LOGGER.info("PytoolsRunServerCommand")

        interpreter = settings.BASE_SETTING.get(settings.INTERPRETER)
        if not interpreter:
            sublime.run_command("pytools_change_interpreter")
            return

        server = r"server\app.py"
        command = environment.get_python_exec_command(interpreter, server)
        workdir = os.path.dirname(__file__)

        try:
            client.run_server(command, workdir)
        finally:
            sublime.status_message("finish running server")


SESSION = client.Session()


class PytoolsShutdownServerCommand(sublime_plugin.ApplicationCommand):
    """shutdown server"""

    def run(self):
        LOGGER.info("PytoolsShutdownServerCommand")

        thread = Thread(target=self.shutdown)
        thread.start()

    @pipe
    def shutdown(self):
        try:
            SESSION.exit()
            client.shutdown()
        except Exception as err:
            LOGGER.debug(f"shutdown error: {err}")
        finally:
            LOGGER.debug("server terminated")


def get_workspace_path(view: sublime.View):
    """get working directory for current view"""

    file_name = view.file_name()
    if not view or not file_name:
        return
    window: sublime.Window = view.window()
    try:
        path = max(
            (folder for folder in window.folders() if file_name.startswith(folder))
        )
    except Exception:
        return os.path.dirname(file_name)
    else:
        return path


ERROR_RESPONSE_PANEL_NAME = "error_response"


def show_error_result(window: sublime.Window, message: str) -> None:
    """show error panel"""

    panel = window.create_output_panel(ERROR_RESPONSE_PANEL_NAME)
    panel.set_read_only(False)
    panel.run_command(
        "append", {"characters": message},
    )
    window.run_command("show_panel", {"panel": f"output.{ERROR_RESPONSE_PANEL_NAME}"})


def hide_error_result(window: sublime.Window) -> None:
    """hide error panel"""
    window.destroy_output_panel(ERROR_RESPONSE_PANEL_NAME)


class PytoolsFormatDocumentCommand(sublime_plugin.TextCommand):
    """document formatting command"""

    def run(self, edit: sublime.Edit):
        if not self.view.match_selector(0, "source.python"):
            return

        LOGGER.info("PytoolsFormatDocumentCommand")

        source = self.view.substr(sublime.Region(0, self.view.size()))
        thread = Thread(target=self.format_document, args=(source,))
        thread.start()

    @pipe
    def format_document(self, source):
        LOGGER.debug("formatting thread")

        try:
            if not SESSION.active:
                path = get_workspace_path(self.view)
                SESSION.start(path)
            formatted = client.document_formatting(source)

        except ConnectionRefusedError:
            LOGGER.debug("server not running")
            sublime.run_command("pytools_run_server")

        except Exception as err:
            LOGGER.debug(f"formatting error: {repr(err)}")
        else:

            result = formatted.get("result")
            if result is not None:
                hide_error_result(self.view.window())
                self.view.run_command(
                    "pytools_apply_document_changes", {"diff": result["diff"]}
                )
                return

            LOGGER.debug(formatted["error"])
            if formatted["error"]["code"] == client.NOT_INITIALIZED:
                path = get_workspace_path(self.view)
                SESSION.start(path)
            else:
                show_error_result(self.view.window(), formatted["error"]["message"])


class DiffHunk:
    """DiffHunk"""

    header_pattern = re.compile(r"@@ \-(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

    def __init__(self, start_remove, end_remove, start_insert, end_insert):
        self.start_remove, self.end_remove = start_remove, end_remove
        self.start_insert, self.end_insert = start_insert, end_insert
        self._removed_text = []
        self._insert_text = []

    def __repr__(self):
        return str(
            {
                "removed": {
                    "start": self.start_remove,
                    "end": self.end_remove,
                    "text": self.removed_text,
                },
                "insert": {
                    "start": self.start_insert,
                    "end": self.end_insert,
                    "text": self.insert_text,
                },
            }
        )

    def append_line(self, text: str):
        if text.startswith(" "):
            self._removed_text.append(text[1:])
            self._insert_text.append(text[1:])
        elif text.startswith("-+"):
            self._insert_text.append(text[2:])
        elif text.startswith("-"):
            self._removed_text.append(text[1:])
        elif text.startswith("+"):
            self._insert_text.append(text[1:])

    @property
    def removed_text(self):
        return "\n".join(self._removed_text)

    @property
    def insert_text(self):
        return "\n".join(self._insert_text)

    @classmethod
    def from_header(cls, diff_header: str):
        match = cls.header_pattern.match(diff_header)
        if not match:
            raise ValueError(f"unable parser diff_header from {diff_header}")

        groups = match.groups()
        remove_span = int(groups[1]) - 1 if groups[1] else 0
        insert_span = int(groups[3]) - 1 if groups[3] else 0
        start_remove = int(groups[0]) - 1  # editor use 0-based line index where diff 1
        end_remove = start_remove + remove_span
        start_insert = int(groups[2]) - 1  # editor use 0-based line index where diff 1
        end_insert = start_insert + insert_span

        return cls(start_remove, end_remove, start_insert, end_insert)


class TextChange:
    """text change item"""

    def __init__(
        self, view: sublime.View, *, start_line: int, end_line: int, new_text: str
    ):
        start_point = view.line(view.text_point(start_line, 0)).a
        end_point = view.line(view.text_point(end_line, 0)).b

        self.region = sublime.Region(start_point, end_point)
        self.new_text = new_text
        # cursor move
        self.cursor_move = len(new_text) - self.region.size()

    def __repr__(self):
        return str({"region": repr(self.region), "new_text": self.new_text})

    def get_region(self, move=0):
        return sublime.Region(self.region.a + move, self.region.b + move)

    @classmethod
    def from_hunk(cls, view: sublime.View, hunk: DiffHunk):
        return cls(
            view,
            start_line=hunk.start_remove,
            end_line=hunk.end_remove,
            new_text=hunk.insert_text,
        )


class PytoolsApplyDocumentChangesCommand(sublime_plugin.TextCommand):
    """apply document changes"""

    def run(self, edit: sublime.Edit, diff: str):
        LOGGER.info(f"apply changes for\n\n{diff}")

        hunks = self.get_hunk(diff)
        self.apply_change(edit, hunks)

    def get_hunk(self, diff: str) -> Iterator:
        hunk = None

        for line in diff.split("\n"):
            if line.startswith("@@"):
                if hunk:
                    # yield current hunk
                    yield hunk
                hunk = DiffHunk.from_header(line)

            # continue if hunk not defined
            if not hunk:
                continue
            # append
            hunk.append_line(line)

        if hunk:
            yield hunk

    def apply_change(self, edit: sublime.Edit, hunks: Iterable[DiffHunk]):
        view: sublime.View = self.view
        changes = [TextChange.from_hunk(view, change) for change in hunks]
        LOGGER.debug(changes)

        move = 0
        for change in changes:
            region = change.get_region(move)
            view.erase(edit, region)
            view.insert(edit, region.a, change.new_text)
            move += change.cursor_move


class DiagnosticItem:
    """Diagnostic item"""

    def __init__(self, severity, row, column, message):
        self.severity = severity
        self.row = row
        self.column = column
        self.message = message

    def __repr__(self):
        return str({"row": self.row, "column": self.column, "message": self.message})

    def get_region(self, view: sublime.View):
        """get region"""

        point = view.text_point(self.row, self.column)
        region: sublime.Region = view.line(point)
        # start selection from defined column
        region.a = point

        # end of line
        if region.a == point:
            region.a -= 1

        return region

    @classmethod
    def from_rpc(cls, data):
        """new from rpc"""
        return cls(data["severity"], data["line"], data["column"], data["message"])


class Diagnostic:
    """diagnostic data holder"""

    panel_name = "pytools_diagnostic"

    region_keys = {
        1: "pytools.error",
        2: "pytools.warning",
        3: "pytools.info",
        4: "pytools.hint",
    }

    def __init__(self):
        self.diagnostics: Dict[str, DiagnosticItem] = {}

    def __repr__(self):
        return str(self.diagnostics)

    def add_diagnostic(self, view: sublime.View, rpc_data):
        """add diagnostic to view"""

        diagnostics = [DiagnosticItem.from_rpc(item) for item in rpc_data]

        self.diagnostics[view.file_name()] = diagnostics
        self.add_regions(view, diagnostics)
        if diagnostics:
            self.show_diagnostic_panel(view)
        else:
            self.hide_diagnostic_panel(view)

    def erase_regions(self, view: sublime.View):
        for _, region_key in self.region_keys.items():
            view.erase_regions(region_key)

    def clean_diagnostic(self, view: sublime.View):
        """clean diagnostic at view"""

        file_name = view.file_name()
        del self.diagnostics[file_name]
        self.erase_regions(view)

        # clean up, allocate new dict to release memory allocation
        if not self.diagnostics:
            self.diagnostics = {}

    def add_regions(self, view: sublime.View, items: List[DiagnosticItem]):
        """add region to view"""

        # clean region in view
        self.erase_regions(view)

        err_region = [
            item.get_region(view) for item in items if item.severity == "error"
        ]
        warn_region = [
            item.get_region(view) for item in items if item.severity == "warning"
        ]
        info_region = [
            item.get_region(view) for item in items if item.severity == "info"
        ]
        hint_region = [
            item.get_region(view) for item in items if item.severity == "hint"
        ]

        for key_map, region in enumerate(
            (hint_region, info_region, warn_region, err_region), start=1
        ):
            LOGGER.debug(f"add region '{self.region_keys[key_map]}' to {repr(region)}")
            view.add_regions(
                key=self.region_keys[key_map],
                regions=region,
                scope="Invalid",
                icon="circle",
                flags=sublime.DRAW_NO_OUTLINE
                | sublime.DRAW_SOLID_UNDERLINE
                | sublime.DRAW_NO_FILL,
            )

    def show_diagnostic_panel(self, view: sublime.View):
        """show diagnostic panel for current view"""

        window: sublime.Window = view.window()
        panel = window.create_output_panel(self.panel_name)
        panel.set_read_only(False)

        try:
            diagnostic_item: List[DiagnosticItem] = self.diagnostics[view.file_name()]
            panel.run_command(
                "append",
                {
                    "characters": "\n".join(
                        [
                            f"{os.path.basename(view.file_name())}:{item.row+1}:{item.column}: {item.message}"
                            for item in diagnostic_item
                        ]
                    )
                },
            )
            window.run_command("show_panel", {"panel": f"output.{self.panel_name}"})

        except KeyError:
            LOGGER.debug(f"no diagnostics report for {view.file_name()}")

        except Exception as err:
            LOGGER.debug(f"error show diagnostic for {view.file_name()}: {repr(err)}")

    def hide_diagnostic_panel(self, view: sublime.View):
        window: sublime.Window = view.window()
        window.destroy_output_panel(self.panel_name)


DIAGNOSTIC = Diagnostic()


class PytoolsCleanDiagnosticCommand(sublime_plugin.TextCommand):
    """clean diagnostic"""

    def run(self, edit):
        DIAGNOSTIC.clean_diagnostic(self.view)
        DIAGNOSTIC.hide_diagnostic_panel(self.view)


class PytoolsPublishDiagnosticCommand(sublime_plugin.TextCommand):
    """document publish diagnostic command"""

    def run(self, edit: sublime.Edit):
        if not self.view.match_selector(0, "source.python"):
            return

        LOGGER.info("PytoolsPublishDiagnosticCommand")

        file_name = self.view.file_name()

        thread = Thread(target=self.publish_diagnostic, args=(file_name,))
        thread.start()

    @pipe
    def publish_diagnostic(self, file_name):
        LOGGER.debug("publish_diagnostic thread")
        try:
            if not SESSION.active:
                path = get_workspace_path(self.view)
                SESSION.start(path)
            source = self.view.substr(sublime.Region(0, self.view.size()))
            diagnostics = client.document_publish_diagnostic(
                source=source, path=file_name
            )

        except ConnectionRefusedError:
            LOGGER.debug("server not running")
            sublime.run_command("pytools_run_server")

        except Exception as err:
            LOGGER.debug(f"publish diagnostic error: {repr(err)}")
        else:
            result = diagnostics.get("result")
            if result is not None:
                DIAGNOSTIC.add_diagnostic(self.view, result)
                return

            LOGGER.debug(diagnostics["error"])
            if diagnostics["error"]["code"] == client.NOT_INITIALIZED:
                path = get_workspace_path(self.view)
                SESSION.start(path)


class CompletionParam:

    # match: string, tuple, dict,list
    access_member = re.compile(r"^(.*[\w\)\}\]\"']\.)\w*$")

    # fmt: off
    nested_import = re.compile(
        r"^(.*\w+\,)\w*$"
        r"|^(.*\w+\,)\s*\w*$"
        r"|^(.*\w+\s*\,)\s*\w*$"
    )
    # fmt: on

    def __init__(self, view: sublime.View):
        # complete on first cursor
        self.start = self.get_completion_point(view)

    def get_completion_point(self, view: sublime.View) -> int:
        """get competion point"""

        cursor = view.sel()[0].a
        line_region = view.line(cursor)

        line_str = view.substr(line_region)[: cursor - line_region.a]
        start_line = line_region.a

        if not line_str:
            return cursor

        if line_str.isspace():
            LOGGER.debug("space")
            raise ValueError("Cancel completion: 'line is space'")

        match = self.access_member.match(line_str)
        if match:
            LOGGER.debug("access_member")
            return start_line + max(len(group) for group in match.groups() if group)

        word_region = view.word(cursor)
        word_str = view.substr(word_region)

        lstrip_line_str = line_str.lstrip()
        if lstrip_line_str.startswith("from") or lstrip_line_str.startswith("import"):

            match = self.nested_import.match(line_str)
            if match:
                LOGGER.debug("nested_import")
                return start_line + max(len(group) for group in match.groups() if group)
            if word_str.isidentifier():
                return word_region.a
            return cursor

        if word_str.isidentifier():
            return word_region.a + 1

        *_, last_char = line_str
        if not str.isidentifier(last_char):
            LOGGER.debug("hanging space")
            raise ValueError("Cancel completion: 'hanging space'")

        return cursor


class CompletionItem(sublime.CompletionItem):

    # Valid values for type are ``module``, ``class``, ``instance``, ``function``,
    # ``param``, ``path``, ``keyword`` and ``statement``
    kind_map = defaultdict(
        lambda: sublime.KIND_AMBIGUOUS,
        {
            "module": sublime.KIND_NAMESPACE,
            "class": sublime.KIND_TYPE,
            "instance": sublime.KIND_VARIABLE,
            "function": sublime.KIND_FUNCTION,
            "param": sublime.KIND_VARIABLE,
            "path": sublime.KIND_AMBIGUOUS,
            "keyword": sublime.KIND_KEYWORD,
            "statement": sublime.KIND_VARIABLE,
        },
    )

    @classmethod
    def from_rpc(cls, rpc_data):
        return cls(
            trigger=rpc_data["label"],
            annotation=rpc_data["annotation"],
            kind=cls.kind_map[rpc_data["type"]],
        )


def is_python_code(view: sublime.View):
    """view is python code"""
    return view.match_selector(0, "source.python")


def is_identifier(view: sublime.View, point: int):
    """point in View is identifier"""

    # f-string
    if view.match_selector(
        point, "meta.string.interpolated.python meta.interpolation.python"
    ):
        return True
    if view.match_selector(point, "meta.string"):
        return False
    if view.match_selector(point, "comment"):
        return False
    return True


class EventListener(sublime_plugin.EventListener):
    def __init__(self):
        self._prev_param = None
        self.completion = None

    @staticmethod
    def _change_workspace(path):
        try:
            client.change_workspace(path)
        except ConnectionError as err:
            LOGGER.debug(err)

    def on_activated(self, view: sublime.View):
        """on view activated"""

        if not is_python_code(view):
            return

        if SESSION.active:
            path = get_workspace_path(view)
            thread = Thread(target=self._change_workspace, args=(path,))
            thread.start()

    def on_post_save(self, view: sublime.View):
        if not is_python_code(view):
            return

        if SESSION.active:
            path = get_workspace_path(view)
            thread = Thread(target=self._change_workspace, args=(path,))
            thread.start()

    def on_query_completions(
        self, view: sublime.View, prefix: Any, locations: Any
    ) -> Optional[Iterable[Any]]:

        if not (is_python_code(view) and is_identifier(view, locations[0])):
            return None

        try:
            param = CompletionParam(view)
        except ValueError:
            view.run_command("hide_auto_complete")
            return None

        if self.completion and self._prev_param:
            if self._prev_param.start == param.start:
                return sublime.CompletionList(
                    self.completion, sublime.INHIBIT_WORD_COMPLETIONS
                )

        thread = Thread(target=self.document_completion, args=(view, param))
        thread.start()
        view.run_command("hide_auto_complete")
        return None

    @pipe
    def document_completion(self, view: sublime.View, param: CompletionParam):
        try:
            if not SESSION.active:
                path = get_workspace_path(view)
                SESSION.start(path)
            source = view.substr(sublime.Region(0, param.start))
            row, col = view.rowcol(param.start)
            row += 1
            completions = client.document_completion(source, row, col)

        except ConnectionRefusedError:
            LOGGER.debug("server not running")
            sublime.run_command("pytools_run_server")

        except ConnectionError as err:
            LOGGER.debug(err)

        else:
            result = completions.get("result")
            if result is not None:
                items = [CompletionItem.from_rpc(item) for item in result]
                LOGGER.debug(f"candidates = {len(items)}")
                self._prev_param = param
                self.completion = items

                view.run_command("hide_auto_complete")
                view.run_command(
                    "auto_complete",
                    {
                        "disable_auto_insert": True,
                        "next_completion_if_showing": False,
                        "auto_complete_commit_on_tab": True,
                    },
                )
                return

            LOGGER.debug(completions["error"])
            if completions["error"]["code"] == client.NOT_INITIALIZED:
                path = get_workspace_path(view)
                SESSION.start(path)

    def on_hover(self, view: sublime.View, point: int, hover_zone: int):
        """on hover"""

        if not is_python_code(view):
            return

        if hover_zone == sublime.HOVER_TEXT:
            if not is_identifier(view, point):
                return

            LOGGER.info("on HOVER_TEXT")

            thread = Thread(target=self.on_hover_text, args=(view, point))
            thread.start()

    @pipe
    def on_hover_text(self, view: sublime.View, point: int):
        try:
            if not SESSION.active:
                path = get_workspace_path(view)
                SESSION.start(path)

            # point to word endpoint
            word = view.word(point)
            end_point = word.b

            source = view.substr(sublime.Region(0, end_point))
            row, col = view.rowcol(end_point)
            row += 1
            documentation = client.document_hover(source, row, col)

        except ConnectionRefusedError:
            LOGGER.debug("server not running")
            sublime.run_command("pytools_run_server")

        except ConnectionError as err:
            LOGGER.debug(err)

        else:
            result = documentation.get("result")
            if result is not None:
                content = result["content"]
                LOGGER.debug(f"result : {content}")

                def on_navigate(link):
                    if link.startswith(":"):
                        file_name = view.file_name()
                        link = "".join([file_name, link])
                    view.window().open_file(link, flags=sublime.ENCODED_POSITION)

                try:
                    view.show_popup(
                        content,
                        flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                        location=point,
                        max_width=1024,
                        on_navigate=on_navigate,
                    )
                except Exception as err:
                    LOGGER.debug(err)

                return

            LOGGER.debug(documentation["error"])
            if documentation["error"]["code"] == client.NOT_INITIALIZED:
                path = get_workspace_path(view)
                SESSION.start(path)


class PytoolsOpenTerminalCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit):
        cwd = get_workspace_path(self.view) or None
        command = ["cmd"]

        interpreter = settings.BASE_SETTING.get(settings.INTERPRETER)
        if interpreter:
            activate_command = environment.get_envs_activate_command(interpreter)
            command = command + ["/K"] + activate_command.split()
            # command = command + ["/K"] + activate_command.split() + ["&&", "powershell"]

        LOGGER.debug(command)
        subprocess.Popen(command, cwd=cwd)
