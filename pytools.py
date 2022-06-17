"""pythools implementation"""

import logging
import re
import os
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from functools import wraps
from threading import Lock, Thread
from typing import Iterable, Iterator, List, Any, Optional, Dict

import sublime
import sublime_plugin

from .api import environment
from .api import client
from .api import settings

LOGGER = logging.getLogger(__name__)
# LOGGER.setLevel(logging.DEBUG)
STREAM_HANDLER = logging.StreamHandler()
LOG_TEMPLATE = "%(levelname)s %(asctime)s %(filename)s:%(lineno)s  %(message)s"
STREAM_HANDLER.setFormatter(logging.Formatter(LOG_TEMPLATE))
LOGGER.addHandler(STREAM_HANDLER)

# features capability

DOCUMENT_COMPLETION = True
DOCUMENT_HOVER = True
DOCUMENT_FORMATTING = True
DOCUMENT_PUBLISH_DIAGNOSTIC = True


def update_feature_capability():
    """update feature capability"""

    LOGGER.info("update feature capability")

    global DOCUMENT_COMPLETION
    global DOCUMENT_HOVER
    global DOCUMENT_FORMATTING
    global DOCUMENT_PUBLISH_DIAGNOSTIC

    DOCUMENT_COMPLETION = settings.BASE_SETTING.get(settings.DOCUMENT_COMPLETION, True)
    DOCUMENT_HOVER = settings.BASE_SETTING.get(settings.DOCUMENT_HOVER, True)
    DOCUMENT_FORMATTING = settings.BASE_SETTING.get(settings.DOCUMENT_FORMATTING, True)
    DOCUMENT_PUBLISH_DIAGNOSTIC = settings.BASE_SETTING.get(
        settings.DOCUMENT_PUBLISH_DIAGNOSTIC, True
    )


def update_builtin_settings():
    """update builtin settings"""

    s = settings.Settings("Python.sublime-settings")
    s.update(
        {
            "auto_complete_use_index": False,
            "index_files": False,
            "show_definitions": False,
            "tab_completion": False,
            "translate_tabs_to_spaces": True,
        }
    )


def plugin_loaded():
    """sublime plugin loaded"""

    # update builtin settings
    update_builtin_settings()

    # load feature capability
    update_feature_capability()
    # add settings change event listener
    settings.BASE_SETTING.add_on_change(
        settings.BASE_CHANGE_LISTENER_KEY, update_feature_capability
    )


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

        self.view: sublime.View = sublime.active_window().active_view()
        self.view.set_status("status_key", "RUNNING SERVER")

        server = r"server\app.py"
        command = environment.get_python_exec_command(interpreter, server)
        workdir = os.path.dirname(__file__)

        thread = Thread(target=self.run_server, args=(command, workdir))
        thread.start()

    def run_server(self, command, workdir):
        try:
            client.run_server(command, workdir)
        except client.AddressInUse as err:
            LOGGER.debug(repr(err))
        except Exception as err:
            LOGGER.error(f"run_server error: {err}")
        finally:
            self.view.erase_status("status_key")
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


class OutputPanel:
    """output panel handler"""

    NAME = "pytools"

    @staticmethod
    def set(message: str):
        """set panel message"""

        panel = sublime.active_window().get_output_panel(OutputPanel.NAME)
        if not panel:
            panel = sublime.active_window().create_output_panel(OutputPanel.NAME)

        panel.set_read_only(False)
        panel.run_command(
            "append", {"characters": message},
        )

    @staticmethod
    def show():
        """show panel"""
        sublime.active_window().run_command(
            "show_panel", {"panel": f"output.{OutputPanel.NAME}"}
        )

    @staticmethod
    def destroy():
        """destroy panel"""
        sublime.active_window().destroy_output_panel(OutputPanel.NAME)


class PytoolsFormatDocumentCommand(sublime_plugin.TextCommand):
    """document formatting command"""

    def run(self, edit: sublime.Edit):
        if not all([self.view.match_selector(0, "source.python"), DOCUMENT_FORMATTING]):
            return

        LOGGER.info("PytoolsFormatDocumentCommand")

        source = self.view.substr(sublime.Region(0, self.view.size()))
        thread = Thread(target=self.format_document, args=(source,))
        thread.start()

    @pipe
    def format_document(self, source):
        LOGGER.debug("formatting thread")

        def apply_changes(result):
            if diff := result.get("diff"):
                self.view.run_command("pytools_apply_document_changes", {"diff": diff})

        try:
            if not SESSION.active:
                path = get_workspace_path(self.view)
                SESSION.start(path)
            response = client.document_formatting(source)

        except ConnectionRefusedError:
            LOGGER.debug("server not running")
            sublime.run_command("pytools_run_server")

        except Exception as err:
            LOGGER.debug(f"formatting error: {repr(err)}")

        else:
            result = response.get("result")
            if result is not None:
                apply_changes(result)
                OutputPanel.destroy()

            if error := response.get("error"):
                if error["code"] == client.NOT_INITIALIZED:
                    path = get_workspace_path(self.view)
                    SESSION.start(path)

                else:
                    OutputPanel.set(error["message"])
                    OutputPanel.show()

    def is_visible(self):
        return self.view.match_selector(0, "source.python")


@dataclass
class DiffHunk:
    """DiffHunk"""

    start_remove: int
    end_remove: int
    start_insert: int
    end_insert: int
    _removed_text: List[str]
    _insert_text: List[str]

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
        """create from diff header"""

        # diff format: `@@ -sub,lines_changed +insert,lines_changed @@`
        if match := re.match(
            r"@@ (?:\-(\d+)(?:,(\d+))? )?(?:\+(\d+)(?:,(\d+))? )?@@", diff_header
        ):
            groups = match.groups()
            remove_span = int(groups[1]) - 1 if groups[1] else 0
            insert_span = int(groups[3]) - 1 if groups[3] else 0

            # editor use 0-based line index where diff 1
            start_remove = int(groups[0]) - 1
            end_remove = start_remove + remove_span

            # editor use 0-based line index where diff 1
            start_insert = int(groups[2]) - 1
            end_insert = start_insert + insert_span

            return cls(start_remove, end_remove, start_insert, end_insert, [], [])

        raise ValueError(f"unable parser diff_header from {diff_header}")


@dataclass
class TextChangeItem:
    """text change item"""

    region: sublime.Region
    new_text: str
    cursor_move: int

    def get_region(self, move=0):
        return sublime.Region(self.region.begin() + move, self.region.end() + move)

    @classmethod
    def from_hunk(cls, view: sublime.View, hunk: DiffHunk, /):
        region = sublime.Region(
            a=view.line(view.text_point(hunk.start_remove, 0)).begin(),
            b=view.line(view.text_point(hunk.end_remove, 0)).end(),
        )
        new_text = hunk.insert_text
        cursor_move = len(new_text) - region.size()
        return cls(region, new_text, cursor_move)


class PytoolsApplyDocumentChangesCommand(sublime_plugin.TextCommand):
    """apply document changes"""

    def run(self, edit: sublime.Edit, diff: str):
        LOGGER.info(f"apply changes for\n\n{diff}")

        hunks = self.get_hunk(diff)
        self.apply_change(edit, hunks)

    def get_hunk(self, diff: str) -> Iterator[DiffHunk]:
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
        text_changes = [TextChangeItem.from_hunk(view, change) for change in hunks]
        LOGGER.debug(text_changes)

        move = 0
        for text_change in text_changes:
            region = text_change.get_region(move)
            view.erase(edit, region)
            view.insert(edit, region.a, text_change.new_text)
            move += text_change.cursor_move


@dataclass
class DiagnosticItem:
    """Diagnostic item"""

    severity: str
    row: int
    column: int
    message: str

    def get_region(self, view: sublime.View):
        """get region"""

        point = view.text_point(self.row - 1, self.column)
        region: sublime.Region = view.line(point)

        if region.end() != point:
            # start selection from defined column
            region.a = point

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
                | sublime.DRAW_SQUIGGLY_UNDERLINE
                | sublime.DRAW_NO_FILL,
            )

    def show_diagnostic_panel(self, view: sublime.View):
        """show diagnostic panel for current view"""

        diagnostic_item: List[DiagnosticItem] = self.diagnostics[view.file_name()]
        message = "\n".join(
            [
                f"{os.path.basename(view.file_name())}:{item.row+1}:{item.column}: {item.message}"
                for item in diagnostic_item
            ]
        )
        OutputPanel.set(message)
        OutputPanel.show()

    def hide_diagnostic_panel(self, view: sublime.View):
        OutputPanel.destroy()


DIAGNOSTIC = Diagnostic()


class PytoolsCleanDiagnosticCommand(sublime_plugin.TextCommand):
    """clean diagnostic"""

    def run(self, edit):
        DIAGNOSTIC.clean_diagnostic(self.view)
        DIAGNOSTIC.hide_diagnostic_panel(self.view)

    def is_visible(self):
        return self.view.match_selector(0, "source.python")


class PytoolsPublishDiagnosticCommand(sublime_plugin.TextCommand):
    """document publish diagnostic command"""

    def run(self, edit: sublime.Edit):
        if not all(
            [self.view.match_selector(0, "source.python"), DOCUMENT_PUBLISH_DIAGNOSTIC]
        ):
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
            response = client.document_publish_diagnostic(source=source, path=file_name)

        except ConnectionRefusedError:
            LOGGER.debug("server not running")
            sublime.run_command("pytools_run_server")

        except Exception as err:
            LOGGER.debug(f"publish diagnostic error: {repr(err)}")
        else:
            result = response.get("result")
            if result is not None:
                DIAGNOSTIC.add_diagnostic(self.view, result)
                return

            if error := response.get("error"):
                if error["code"] == client.NOT_INITIALIZED:
                    path = get_workspace_path(self.view)
                    SESSION.start(path)

    def is_visible(self):
        return self.view.match_selector(0, "source.python")


class CompletionParam:
    """completion param"""

    def __init__(self, view: sublime.View):
        # complete on first cursor
        self.location = self.get_completion_point(view)
        self.source = view.substr(sublime.Region(0, self.location))

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

        # trigger completion for identifier
        if found := re.search(r"([A-Za-z]\w*\.)\w*$", line_str):
            dot_index = found.group(1).index(".")
            # set cursor next to dot
            return start_line + found.start() + dot_index + 1

        # trigger completion for string, dict, set, tuple, list
        if found := re.search(r"([\w\"'\}\]\)]\.)\w*$", line_str):
            dot_index = found.group(1).index(".")
            # set cursor next to dot
            return start_line + found.start() + dot_index + 1

        word_region = view.word(cursor)
        word_str = view.substr(word_region)

        if match := re.match(r"^\s*(?:import|from)", line_str):
            if found := re.search(r"(\w+\s*,)\s*\w*$", line_str):
                comma_index = found.group(1).index(",")
                # set cursor next to comma
                return start_line + found.start() + comma_index + 1

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
            "property": sublime.KIND_VARIABLE,
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


POPUP_STYLE = """
body {
    margin: 0.8em;
}
code, .code_block {
    background-color: color(var(--background) alpha(0.8));
    font-family: ui-monospace,SFMono-Regular,SF Mono,Menlo,Consolas,Liberation Mono,monospace;
    border-radius: 0.4em;
}

code {
    padding: 0 0.4em 0 0.4em;
}

.code_block {
    padding: 0.4em;
}
"""


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

        if not all(
            [
                is_python_code(view),
                is_identifier(view, locations[0]),
                DOCUMENT_COMPLETION,
            ]
        ):
            return None

        try:
            param = CompletionParam(view)
        except ValueError:
            view.run_command("hide_auto_complete")
            return None

        if self.completion and self._prev_param:
            if (
                self._prev_param.location == param.location
                and self._prev_param.source == param.source
            ):
                return sublime.CompletionList(
                    self.completion, sublime.INHIBIT_WORD_COMPLETIONS
                )

        thread = Thread(target=self.document_completion, args=(view, param))
        thread.start()
        view.run_command("hide_auto_complete")
        return None

    @pipe
    def document_completion(self, view: sublime.View, param: CompletionParam):
        """document completion task"""

        def trigger_completion():
            view.run_command("hide_auto_complete")
            view.run_command(
                "auto_complete",
                {
                    "disable_auto_insert": True,
                    "next_completion_if_showing": False,
                    "auto_complete_commit_on_tab": True,
                },
            )

        def show_completion(result):
            items = [CompletionItem.from_rpc(item) for item in result]
            LOGGER.debug(f"candidates = {len(items)}")
            self._prev_param = param
            self.completion = items
            trigger_completion()

        try:
            if not SESSION.active:
                path = get_workspace_path(view)
                SESSION.start(path)
            source = param.source
            row, col = view.rowcol(param.location)
            row += 1
            response = client.document_completion(source, row, col)

        except ConnectionRefusedError:
            LOGGER.debug("server not running")
            sublime.run_command("pytools_run_server")

        except ConnectionError as err:
            LOGGER.debug(err)

        else:
            result = response.get("result")
            if result is not None:
                show_completion(result)

            if error := response.get("error"):
                if error["code"] == client.NOT_INITIALIZED:
                    path = get_workspace_path(view)
                    SESSION.start(path)

    def on_hover(self, view: sublime.View, point: int, hover_zone: int):
        """on hover"""

        if not is_python_code(view):
            return

        if hover_zone == sublime.HOVER_TEXT:
            if not all([is_identifier(view, point), DOCUMENT_HOVER]):
                return

            LOGGER.info("on HOVER_TEXT")

            thread = Thread(target=self.on_hover_text, args=(view, point))
            thread.start()

    @pipe
    def on_hover_text(self, view: sublime.View, point: int):
        """on hover text task"""

        def on_navigate(link):
            if link.startswith(":"):
                link = "".join([view.file_name(), link])
            view.window().open_file(link, flags=sublime.ENCODED_POSITION)

        def show_documentation(result):
            content = result.get("content")
            if not content:
                return

            # add css style
            content = f"<style>{POPUP_STYLE}</style>\n{content}" if content else ""

            view.show_popup(
                content,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                location=point,
                max_width=1024,
                on_navigate=on_navigate,
            )

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
            response = client.document_hover(source, row, col)

        except ConnectionRefusedError:
            LOGGER.debug("server not running")
            sublime.run_command("pytools_run_server")

        except ConnectionError as err:
            LOGGER.debug(err)

        else:
            result = response.get("result")
            if result is not None:
                show_documentation(result)

            error = response.get("error")
            if error:
                if error["code"] == client.NOT_INITIALIZED:
                    path = get_workspace_path(view)
                    SESSION.start(path)


class PytoolsOpenTerminalCommand(sublime_plugin.TextCommand):
    """open terminal"""

    def run(self, edit: sublime.Edit, current_file_directory=False):

        # TODO: implement for posix

        emulator = settings.BASE_SETTING.get(settings.TERMINAL_EMULATOR)
        emulator = emulator if emulator else "cmd"
        command = [emulator]

        if current_file_directory:
            LOGGER.debug("open in current file directory")
            workdir = os.path.dirname(self.view.file_name())
        else:
            workdir = get_workspace_path(self.view) or None

        if not is_python_code(self.view):
            # bypass activate python environment
            self.open_terminal(command, workdir)
            return

        interpreter = settings.BASE_SETTING.get(settings.INTERPRETER)
        if interpreter:
            activate_command = environment.get_envs_activate_command(interpreter)
            command_map = {
                "cmd": ["cmd", "/K"] + activate_command.split(),
                "powershell": ["cmd", "/K"]
                + activate_command.split()
                + ["&&", "powershell"],
            }
            command = command_map[emulator]

        LOGGER.debug(command)

        self.open_terminal(command, workdir)

    def open_terminal(self, command, workdir=None):
        subprocess.Popen(command, cwd=workdir)


class PytoolsChangeTerminalEmulatorCommand(sublime_plugin.WindowCommand):
    """open settings"""

    def run(self, open_default=False):

        # TODO: implement for posix

        window: sublime.Window = self.window
        items = ["cmd", "powershell"]

        def on_select(index=-1):
            if index > -1:
                settings.BASE_SETTING.set(settings.TERMINAL_EMULATOR, items[index])

        try:
            current = settings.BASE_SETTING.get(settings.TERMINAL_EMULATOR)
            index = items.index(current)
        except ValueError:
            index = 0

        window.show_quick_panel(
            items,
            on_select=on_select,
            flags=sublime.KEEP_OPEN_ON_FOCUS_LOST,
            selected_index=index,
        )
