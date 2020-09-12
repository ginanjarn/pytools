import sublime # pylint: disable=import-error
import sublime_plugin # pylint: disable=import-error
import difflib
import subprocess
import threading
import os
# from .completion.client import Client
from .langserver.client.service import Client # pylint: disable=relative-beyond-top-level
from .langserver.client.sublimetext import completion, hover # pylint: disable=relative-beyond-top-level


def load_settings(key):
    s = sublime.load_settings("Pytools.sublime-settings")
    return s.get(key)


def get_sysenv():
    new_paths = load_settings("path")
    env = os.environ.copy()
    env['PATH'] = new_paths + os.path.pathsep + env['PATH']
    return env


def diff_sanity_check(a, b):
    if a != b:
        raise Exception("diff sanity check mismatch\n-%s\n+%s" % (a, b))


class PytoolsFormatCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        src = view.substr(sublime.Region(0, view.size()))
        fmt_env = get_sysenv()

        try:
            fmt_process_cmd = ["autopep8", "-"]

            if os.name == "nt":
                # linux subprocess module does not have STARTUPINFO
                # so only use it if on Windows
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
                fmt_proc = subprocess.Popen(fmt_process_cmd,shell=True,
                                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=fmt_env, startupinfo=si, bufsize=-1)
            else:
                fmt_proc = subprocess.Popen(fmt_process_cmd,shell=True,
                                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=fmt_env, bufsize=-1)

            sout,serr = fmt_proc.communicate(src.encode())
        except BrokenPipeError:
            print("autopep8 not found in PATH")
            return

        if fmt_proc.returncode != 0:
            print(serr.decode(), end="")
            return

        newsrc = sout.decode()
        diff = difflib.ndiff(src.splitlines(), newsrc.splitlines())
        i = 0
        for line in diff:
            if line.startswith("?"):  # skip hint lines
                continue

            l = (len(line)-2)+1
            if line.startswith("-"):
                diff_sanity_check(view.substr(
                    sublime.Region(i, i+l-1)), line[2:])
                view.erase(edit, sublime.Region(i, i+l))
            elif line.startswith("+"):
                view.insert(edit, i, line[2:]+"\n")
                i += l
            else:
                diff_sanity_check(view.substr(
                    sublime.Region(i, i+l-1)), line[2:])
                i += l


class Pytools(sublime_plugin.EventListener):
    def __init__(self):
        self.completions = None
        self.lsp_client = None
        self.lsp_process = False

    def init_lsp_client(self):
        python = load_settings("python")
        env = get_sysenv()
        self.lsp_client = Client(python=python,env=env)
        # self.lsp_client.initialize()
        thread = threading.Thread(target=self.lsp_client.initialize)
        thread.start()

    def fetch_completions(self, view, prefix, locations):        
        cursor = locations[0]
        src = view.substr(sublime.Region(0, cursor))
        row, col = view.rowcol(cursor)

        if not self.lsp_client:
            return
        raw_completion = self.lsp_client.complete(src,row,col)
        # print("->>",raw_completion)
        completions = completion.format_code(raw_completion)
        # print("<<-",completions)
        # print(repr(completions))
        if completions:
            self.completions = completions
            self.open_query_completions(view)

        # release lock
        self.lsp_process = False

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

        # prevent call multiple process
        self.lsp_process = True

        if not self.lsp_client:
            self.init_lsp_client()
            return

        thread = threading.Thread(
            target=self.fetch_completions, args=(view, prefix, locations))
        thread.start()

    def fetch_help(self,view,point):
        word_region = view.word(point)
        print(word_region)
        word = view.substr(word_region)
        if word.startswith(" "):
            self.lsp_process = False
            return
        print(view.substr(word_region))
        src = view.substr(sublime.Region(0, word_region.b))
        line, col = view.rowcol(point)
        # print(src)
        raw_help = self.lsp_client.hover(src,line,col)
        print(raw_help)
        help_data = hover.format_code(raw_help)
        print(help_data)
        hover.show_popup(view=view,content=help_data,location=point)
        # if err:
        #     print(err)
        #     return
        # print(help_data)
        self.lsp_process = False

    def on_hover(self, view, point, hover_zone):
        if hover_zone == sublime.HOVER_TEXT:
            # print(point)
            # print(view.word(point))
            # print(view.substr(view.word(point)))
            self.lsp_process = True
            if not self.lsp_client:
                self.init_lsp_client()
                return

            thread = threading.Thread(target=self.fetch_help,args=(view,point))
            thread.start()
        else:
            return
