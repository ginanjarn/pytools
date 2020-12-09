import sublime  # pylint: disable=import-error
import sublime_plugin  # pylint: disable=import-error
import subprocess
import threading
import os
import logging
from .langserver.client.service_v2 import Client  # pylint: disable=relative-beyond-top-level
from .langserver.client.sublimetext import completion, hover, formatting  # pylint: disable=relative-beyond-top-level

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


class ThreadRunning(Exception):
    pass

class InvalidSelector(Exception):
    pass

class InvalidWord(Exception):
    pass

def plugin_loaded():
    settings = sublime.load_settings("Preferences.sublime-settings")
    settings.set("show_definitions", False)
    triggers = [
        {"selector": "source.python", "characters": "."}
    ]
    settings.set("auto_complete_triggers", triggers)
    sublime.save_settings("Preferences.sublime-settings")

    s = sublime.load_settings("Pytools.sublime-settings")
    s.add_on_change("path", CLIENT_HUB.load_runtime)


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


class ClientHub(Client):
    def __init__(self):
        super().__init__()
        self.lock = threading.Lock()

    def runnable(self, func):
        with self.lock:
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper

    def load_runtime(self):
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
        self.set_python_runtime(python=python, env=env)


CLIENT_HUB = ClientHub()


class PytoolsFormatCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        src = view.substr(sublime.Region(0, view.size()))

        if not view.match_selector(0, "source.python"):
            return
        
        if CLIENT_HUB.ready():
            self.do_formatting(edit)
        else:
            CLIENT_HUB.load_runtime()
            CLIENT_HUB.runnable(CLIENT_HUB.initialize())

    @CLIENT_HUB.runnable
    def do_formatting(self, edit):
        view = self.view
        src = view.substr(sublime.Region(0, view.size()))
        try:
            result = CLIENT_HUB.formatting(src)
            logger.debug(result)
            formatting.update_edit(view, edit, result)
        except Exception:
            logger.debug("formatting exception", exc_info=True)

    def is_visible(self):
        view = self.view
        if not view.match_selector(0, "source.python"):
            return False
        return True


class Pytools(sublime_plugin.EventListener):

    def __init__(self):
        self.service_loaded = None
        self.completions = None

        self._current_prefix = ""
        self._current_pos = 0

        self.completion_thread = None
        self.hover_thread = None

    def load_service(self):
        try:
            CLIENT_HUB.load_runtime()
            self.service_loaded = True
            logger.debug("load_service")
        except:
            pass

    def valid_scope(self, view, location):
        if not view.match_selector(location, "source.python"):
            raise InvalidSelector
        if view.match_selector(location, "comment") or view.match_selector(location, "meta.string"):
            raise InvalidSelector
        return True

    @CLIENT_HUB.runnable
    def fetch_completions(self, view, prefix, locations):
        cursor = locations[0]
        src = view.substr(sublime.Region(0, cursor))

        word = view.word(cursor)
        word_offset = word.a
        if src.endswith(".") or src.endswith(""):
            word_offset = cursor
        if view.match_selector(cursor, "source.python meta.function-call.arguments.python"):
            word_offset = cursor

        row, col = view.rowcol(word_offset)
        if CLIENT_HUB.ready():
            CLIENT_HUB.set_workspace_config(path=os.path.dirname(view.file_name()))
            results = CLIENT_HUB.complete(src,row,col)
            logger.debug(results)
            completions = completion.format_code(results)
            self.completions = completions
            logger.debug(self.completions)

            if self.show_completion(cursor, prefix):
                self.open_query_completions(view)
        else:
            if not self.service_loaded:
                self.load_service()
            CLIENT_HUB.initialize()

    def open_query_completions(self, view):
        """Opens (forced) the sublime autocomplete window"""

        view.run_command("hide_auto_complete")
        view.run_command("auto_complete", {
            "disable_auto_insert": True,
            "next_completion_if_showing": False,
            "auto_complete_commit_on_tab": True,
        })

    def show_completion(self, pos, prefix):
        show = False
        logger.debug("_current_pos = %s, pos = %s",self._current_pos,pos)
        logger.debug("_current_prefix = %s, prefix = %s",self._current_prefix,prefix)
        if self._current_pos == pos or self._current_prefix.startswith(prefix):
            show = True
        if self.completions is None:
            show = False
        logger.debug("show_completion : %s",show)
        return show

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

        try:
            if self.valid_scope(view, location):
                self._current_prefix = prefix
                self._current_pos = location

                def make_completion(cmpl):
                    return (cmpl, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

                completions = None

                if self.completions is not None:
                    completions = self.completions
                    self.completions = None
                else:
                    def make_thread():
                        thread = threading.Thread(target=self.fetch_completions,
                            args=(view,prefix,locations))
                        return thread
                    if self.completion_thread is None:
                        self.completion_thread = make_thread()                        
                    else:
                        if self.completion_thread.is_alive():
                            raise ThreadRunning
                        else:
                            self.completion_thread = make_thread()
                    self.completion_thread.start()

                if completions is None:
                    completions = []
                return make_completion(completions)
                
        except InvalidSelector:
            logger.debug("InvalidSelector")
        except ThreadRunning:
            logging.debug("ThreadRunning")
        except Exception:
            logger.exception("completion exception")

    @CLIENT_HUB.runnable
    def fetch_help(self, view, point):    
        word_region = view.word(point)

        src = view.substr(sublime.Region(0, word_region.b))
        row, col = view.rowcol(point)

        if CLIENT_HUB.ready():
            CLIENT_HUB.set_workspace_config(path=os.path.dirname(view.file_name()))
            result = CLIENT_HUB.hover(src,row,col)
            logger.debug(result)
            formatted_result = hover.format_code(result)
            hover.show_popup(view=view, content=formatted_result, location=point)
        else:
            if not self.service_loaded:
                self.load_service()
            CLIENT_HUB.initialize()

    def on_hover(self, view, point, hover_zone):
        try:
            if self.valid_scope(view, point):
                if hover_zone == sublime.HOVER_TEXT:
                    word_region = view.word(point)
                    if not str.isidentifier(view.substr(word_region)):
                        raise InvalidWord

                    def make_thread():
                        thread = threading.Thread(target=self.fetch_help,
                            args=(view, point))
                        return thread
                    if self.hover_thread is None:
                        self.hover_thread = make_thread()
                    else:
                        if self.hover_thread.is_alive():
                            raise ThreadRunning
                        else:
                            self.hover_thread = make_thread()
                    self.hover_thread.start()

        except InvalidSelector:
            logger.debug("InvalidSelector")
        except InvalidWord:
            logger.debug("InvalidWord")
        except ThreadRunning:
            logger.debug("ThreadRunning")
        except Exception:
            logger.exception("hover exception", exc_info=True)


class PytoolsShutdownserverCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        thread = threading.Thread(target=self.exit_thread)
        thread.start()

    @CLIENT_HUB.runnable
    def exit_thread(self):
        try:            
            CLIENT_HUB.exit()
            logger.info("server terminated")
        except InvalidSelector:
            logger.debug("InvalidSelector")
        except Exception:
            logger.exception("exit exception", exc_info=True)
