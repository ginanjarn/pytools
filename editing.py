import sublime  # pylint: disable=import-error
import sublime_plugin  # pylint: disable=import-error
import difflib
import subprocess
import threading
import os
# from .completion.client import Client
from .langserver.client.service import Client  # pylint: disable=relative-beyond-top-level
from .langserver.client.sublimetext import completion, hover, formatting  # pylint: disable=relative-beyond-top-level


def load_settings(key):
    s = sublime.load_settings("Pytools.sublime-settings")
    return s.get(key)


def get_sysenv():
    new_paths = load_settings("path")
    env = os.environ.copy()
    env['PATH'] = new_paths + os.path.pathsep + env['PATH']
    return env


class PytoolsFormatCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        src = view.substr(sublime.Region(0, view.size()))

        if not view.match_selector(0, "source.python"):
            return

        view.set_status("lsp_process", "🔄 Formatting")

        python = load_settings("python")
        env = get_sysenv()
        lsp_client = Client(python=python, env=env)
        lsp_client.initialize()
        result = lsp_client.formatting(src)
        if not result:
            result = lsp_client.formatting(src)
        formatting.update_edit(view, edit, result)

    def is_visible(self):
        view = self.view
        if not view.match_selector(0, "source.python"):
            return False
        return True


class Pytools(sublime_plugin.EventListener):
    def __init__(self):
        self.completions = None
        self.lsp_client = None
        self.lsp_process = False
        self._prefix = ""

    def init_lsp_client(self, view):
        python = load_settings("python")
        env = get_sysenv()
        env["PATH"] = os.pathsep.join(view.window().folders()) + os.pathsep + env['PATH']
        self.lsp_client = Client(python=python, env=env)
        # self.lsp_client.initialize()
        thread = threading.Thread(target=self.lsp_client.initialize)
        thread.start()

    def fetch_completions(self, view, prefix, locations):
        cursor = locations[0]
        src = view.substr(sublime.Region(0, cursor))
        row, col = view.rowcol(cursor)

        if not self.lsp_client:
            return
        raw_completion = self.lsp_client.complete(src, row, col)
        # print("->>",raw_completion)
        completions = completion.format_code(raw_completion)
        # print("<<-",completions)
        # print(repr(completions))
        if completions:
            self.completions = completions
            self.open_query_completions(view)

        # release lock
        self.lsp_process = False
        view.erase_status("lsp_process")

    def open_query_completions(self, view):
        """Opens (forced) the sublime autocomplete window"""

        view.run_command("hide_auto_complete")
        view.run_command("auto_complete", {
            "disable_auto_insert": True,
            "next_completion_if_showing": False,
            "auto_complete_commit_on_tab": True,
        })

    def on_query_completions(self, view, prefix, locations):
        """Sublime autocomplete event handler.

        Get completions depends on current cursor position and return
        them as list of ('possible completion', 'completion type')

        :param view: currently active sublime view
        :type view: sublime.View
        :param prefix: string for completions
        :type prefix: basestring
        :param locations: offset from beginning
        :type locations: int

        :return: list of tuple(str, str)
        """
        location = locations[0]

        if not view.match_selector(location, "source.python"):
            return

        if self.completions:
            completions = self.completions
            # print("--->",completions)
            self.completions = None
            return (completions, sublime.INHIBIT_WORD_COMPLETIONS)

        old_prefix = self._prefix
        # print(prefix, old_prefix)
        self._prefix = prefix
        if prefix.startswith(old_prefix):
            return
        # print("completing",prefix)
        # prevent call multiple process
        self.lsp_process = True
        view.set_status("lsp_process", "🔄 Completing")

        if not self.lsp_client:
            self.init_lsp_client(view)
            return

        thread = threading.Thread(
            target=self.fetch_completions, args=(view, prefix, locations))
        thread.start()
        return ([], sublime.INHIBIT_WORD_COMPLETIONS)

    def fetch_help(self, view, point):
        word_region = view.word(point)
        word = view.substr(word_region)
        if point == word_region.b:
            self.lsp_process = False
            view.erase_status("lsp_process")
            return
        src = view.substr(sublime.Region(0, word_region.b))
        line, col = view.rowcol(point)
        # print(src)
        raw_help = self.lsp_client.hover(src, line, col)
        # print(raw_help)
        help_data = hover.format_code(raw_help)
        # print(help_data)
        hover.show_popup(view=view, content=help_data, location=point)
        self.lsp_process = False
        view.erase_status("lsp_process")

    def on_hover(self, view, point, hover_zone):
        if not view.match_selector(point, "source.python"):
            return

        if hover_zone == sublime.HOVER_TEXT:
            # print(point)
            # print(view.word(point))
            # print(view.substr(view.word(point)))
            self.lsp_process = True
            view.set_status("lsp_process", "🔄 Documentation")
            if not self.lsp_client:
                self.init_lsp_client(view)
                view.erase_status("lsp_process")
                return

            thread = threading.Thread(
                target=self.fetch_help, args=(view, point))
            thread.start()
        else:
            return

class PytoolsResetserverCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        src = view.substr(sublime.Region(0, view.size()))
        python = load_settings("python")
        env = get_sysenv()
        lsp_client = Client(python=python, env=env)
        lsp_client.initialize()
        lsp_client.exit()

    def is_visible(self):
        view = self.view
        if not view.match_selector(0, "source.python"):
            return False
        return True
