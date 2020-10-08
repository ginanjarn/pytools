import sublime  # pylint: disable=import-error
import sublime_plugin  # pylint: disable=import-error
import difflib
import subprocess
import threading
import os
import logging
from .langserver.client.service import Client  # pylint: disable=relative-beyond-top-level
from .langserver.client.sublimetext import completion, hover, formatting  # pylint: disable=relative-beyond-top-level

logging.basicConfig(format='%(levelname)s: %(asctime)s  %(name)s: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def plugin_loaded():
    settings = sublime.load_settings("Preferences.sublime-settings")
    settings.set("show_definitions", False)
    triggers = [
        {"selector": "source.python", "characters": "."}
    ]
    settings.set("auto_complete_triggers", triggers)
    sublime.save_settings("Preferences.sublime-settings")


def load_settings(key):
    s = sublime.load_settings("Pytools.sublime-settings")
    value = s.get(key)
    if not value:
        logger.error("setting %s not found", key)
        return None
    return value


def get_sysenv():
    new_paths = load_settings("path")

    if new_paths == None:
        logger.error("python environment not configured")
        return

    env = os.environ.copy()
    try:
        env['PATH'] = new_paths + os.path.pathsep + env['PATH']
        return env
    except Exception as e:
        logger.error("invalid environment value", exc_info=True)
        return None


class ClientHub:
    _instance = None

    def __new__(cls):
        if not ClientHub._instance:
            ClientHub._instance = Client()
        return ClientHub._instance

    def __getattribute__(self, name):
        return getattr(self._instance, name)

    def __setattr__(self, name):
        return setattr(self._instance, name)


clientHub = ClientHub()


class PytoolsFormatCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        src = view.substr(sublime.Region(0, view.size()))

        if not view.match_selector(0, "source.python"):
            return

        view.set_status("lsp_process", "🔄 Formatting")

        python = load_settings("python")
        env = get_sysenv()

        if python == None and env == None:
            logger.warning("python environment not configured")
            msg = "Python environment not configured.\nSetup now?"
            setup = sublime.ok_cancel_dialog(msg, "Yes")
            if setup:
                view.run_command("pytools_environment_setup")
            return

        global clientHub
        if not clientHub.capabilities:
            logger.warning("not initialized")
            env["PATH"] = os.pathsep + env['PATH']
            clientHub.change_python(python=python, env=env)
            clientHub.initialize()
        result = clientHub.formatting(src)
        formatting.update_edit(view, edit, result)
        view.erase_status("lsp_process")

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
        self.cached_completion = {}
        self.cached_completion_params = {}

    def preprocess_lsp(self, view):
        global clientHub
        python = load_settings("python")
        env = get_sysenv()

        if python == None and env == None:
            logger.warning("python environment not configured")
            msg = "Python environment not configured.\nSetup now?"
            setup = sublime.ok_cancel_dialog(msg, "Yes")
            if setup:
                view.run_command("pytools_environment_setup")
            return

        env["PATH"] = os.pathsep + env['PATH']
        clientHub.change_python(python=python, env=env)
        if not clientHub.capabilities:
            clientHub.initialize()
        path = os.path.dirname(view.file_name())
        config = {"jedi": {"project": {"path": path}}}
        clientHub.workspace_config_change(config)

    def fetch_completions(self, view, prefix, locations):
        cursor = locations[0]
        src = view.substr(sublime.Region(0, cursor))
        word = view.word(cursor)

        word_offset = word.a
        logger.debug(view.substr(word))
        # FIXME: invalid cursor on dot(".") character

        if view.substr(word) == ".":
            word_offset = cursor
            # src = view.substr(sublime.Region(0, word_offset))

        row, col = view.rowcol(word_offset)
        code_token = "%s:%s" % (view.file_name(), word_offset)
        logger.debug("code_token = %s",code_token)

        if view.match_selector(cursor,"source.python meta.function-call.arguments.python"):
            logger.debug("inside function-call")
            func_regions = view.find_by_selector("source.python meta.function-call.arguments.python")
            func_region = [r for r in func_regions if r.a<cursor<r.b]
            if len(func_region)>0:
                logger.debug(func_region[0])
                func = view.word(func_region[0].a-2)
                param_token = "%s:%s"%(view.file_name(),func.a)
                logger.debug("param token : %s",param_token)
                cached_params = self.cached_completion_params.get(param_token)
                if cached_params:
                    logger.debug("cached_params available")
                    completions, old_src = cached_params
                    # src = view.substr(sublime.Region(0,func.a))
                    src = src[:func.a]
                    logger.debug("is equal => %s ? %s",src[-5:], old_src[-5:])
                    if src == old_src:
                        logger.debug(completions)
                        self.completions = completions[view.substr(func)]
                        logger.debug("completion params => %s",self.completions)
                        self._old_prefix = prefix
                        self.open_query_completions(view)
                        # release lock
                        self.lsp_process_count -= 1
                        view.erase_status("lsp_process")
                        return

            # release completing, return nothing
            self.lsp_process_count -= 1
            view.erase_status("lsp_process")
            return

        cached_completion = self.cached_completion.get(code_token)
        if cached_completion:
            completions, old_src = cached_completion
            if src[:word_offset] == old_src:
                self.completions = completions
                self._old_prefix = prefix
                self.open_query_completions(view)
                # release lock
                self.lsp_process_count -= 1
                view.erase_status("lsp_process")
                return
            else:
                logger.debug("code changed")
                del self.cached_completion[code_token]
                del self.cached_completion_params[code_token]

        logger.debug("no cached_completion")
        global clientHub
        self.preprocess_lsp(view)
        raw_completion = clientHub.complete(src[:word_offset], row, col)
        # logger.debug(raw_completion)
        completions = completion.format_code(raw_completion)
        params = completion.get_params(raw_completion)
        logger.debug("fetch_completions")
        if completions:
            self.cached_completion[code_token] = (completions, src[:word_offset])
            self.cached_completion_params[code_token] = (params, src[:word_offset])
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

        if self.lsp_process_count >= 1:
            return empty_completions
        self.lsp_process_count += 1
        view.set_status("lsp_process", "🔄 Completing")

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

        global clientHub
        self.preprocess_lsp(view)
        raw_help = clientHub.hover(src, line, col)
        logger.debug(raw_help)
        help_data = hover.format_code(raw_help)
        hover.show_popup(view=view, content=help_data, location=point)
        # release lock
        self.lsp_process_count -= 1
        view.erase_status("lsp_process")

    def on_hover(self, view, point, hover_zone):
        if not view.match_selector(point, "source.python"):
            return
        if view.match_selector(point, "source.python comment.line.number-sign.python"):
            return

        if hover_zone == sublime.HOVER_TEXT:
            if self.lsp_process_count >= 1:
                return
            self.lsp_process_count += 1
            view.set_status("lsp_process", "🔄 Documentation")
            thread = threading.Thread(
                target=self.fetch_help, args=(view, point))
            thread.start()
        else:
            return


class PytoolsResetserverCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        thread = threading.Thread(target=self.exit_thread)
        thread.start()

    def exit_thread(self):
        global clientHub
        clientHub.exit()
        logger.info("server terminated")

    def is_visible(self):
        view = self.view
        if not view.match_selector(0, "source.python"):
            return False
        return True
