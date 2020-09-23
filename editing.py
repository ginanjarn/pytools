import sublime  # pylint: disable=import-error
import sublime_plugin  # pylint: disable=import-error
import difflib
import subprocess
import threading
import os
from .langserver.client.service import Client  # pylint: disable=relative-beyond-top-level
from .langserver.client.sublimetext import completion, hover, formatting  # pylint: disable=relative-beyond-top-level


def plugin_loaded():
    settings = sublime.load_settings("Preferences.sublime-settings")
    settings.set("show_definitions", False)
    triggers = [
        {"selector": "source.python", "characters": "."},
        {"selector": "source.python meta.qualified-name.python meta.generic-name.python", "characters": "("}
    ]
    settings.set("auto_complete_triggers", triggers)
    sublime.save_settings("Preferences.sublime-settings")


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
        self.lsp_process_count = 0
        self._old_prefix = ""
        self._workspace_config = None

    def init_lsp_client(self, view):
        python = load_settings("python")
        env = get_sysenv()
        env["PATH"] = os.pathsep.join(
            view.window().folders()) + os.pathsep + env['PATH']
        self.lsp_client = Client(python=python, env=env)
        thread = threading.Thread(target=self.lsp_client.initialize)
        thread.start()

    def fetch_completions(self, view, prefix, locations):
        cursor = locations[0]
        src = view.substr(sublime.Region(0, cursor))
        row, col = view.rowcol(cursor)

        raw_completion = self.lsp_client.complete(src, row, col)
        completions = completion.format_code(raw_completion)
        if completions:
            self.completions = completions
            self._old_prefix = prefix
            self.open_query_completions(view)

        # release lock
        self.lsp_process_count -= 1
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
        if view.match_selector(location, "meta.string.python"):
            return

        empty_completions = ([], sublime.INHIBIT_WORD_COMPLETIONS)

        if self.completions:
            completions = self.completions
            self.completions = None
            
            if prefix.startswith(self._old_prefix) or self._old_prefix == "":
                return (completions, sublime.INHIBIT_WORD_COMPLETIONS)
            else:
                return empty_completions
        
        if self.lsp_process_count > 1:
            return empty_completions
        self.lsp_process_count += 1
        view.set_status("lsp_process", "🔄 Completing")

        if not self.lsp_client:
            self.init_lsp_client(view)
            return empty_completions
        if not self._workspace_config:
            self.change_workspace_config(view)

        thread = threading.Thread(
            target=self.fetch_completions, args=(view, prefix, locations))
        thread.start()
        return empty_completions

    def fetch_help(self, view, point):
        word_region = view.word(point)
        if point == word_region.b:
            self.lsp_process_count -= 1
            view.erase_status("lsp_process")
            return
        src = view.substr(sublime.Region(0, word_region.b))
        line, col = view.rowcol(point)
        raw_help = self.lsp_client.hover(src, line, col)
        help_data = hover.format_code(raw_help)
        hover.show_popup(view=view, content=help_data, location=point)
        # release lock
        self.lsp_process_count -= 1
        view.erase_status("lsp_process")

    def on_hover(self, view, point, hover_zone):
        if not view.match_selector(point, "source.python"):
            return
        if view.match_selector(point,"source.python comment.line.number-sign.python"):
            return

        if hover_zone == sublime.HOVER_TEXT:
            if self.lsp_process_count > 1:
                return
            self.lsp_process_count += 1
            view.set_status("lsp_process", "🔄 Documentation")
            if not self.lsp_client:
                self.init_lsp_client(view)
                view.erase_status("lsp_process")
                return

            if not self._workspace_config:
                self.change_workspace_config(view)
            thread = threading.Thread(
                target=self.fetch_help, args=(view, point))
            thread.start()
        else:
            return

    def on_activated(self, view):
        if not view.match_selector(0, "source.python"):
            return
        self.change_workspace_config(view)

    def change_workspace_config(self, view):
        if not self.lsp_client:
            return
        config = {"path": os.path.dirname(view.file_name())}
        self._workspace_config = config
        def do():
            self.lsp_client.workspace_config_change(self._workspace_config)
        thread = threading.Thread(target=do)
        thread.run()


class PytoolsResetserverCommand(sublime_plugin.TextCommand):
    def run(self, edit):        
        thread = threading.Thread(target=self.exit_thread)
        thread.start()

    def exit_thread(self):
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
