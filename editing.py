import sublime
import sublime_plugin
import difflib
import subprocess
import os


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

        try:
            fmt = subprocess.Popen(["autopep8", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, creationflags=0x08000000, env=get_sysenv(), shell=True)
            sout, serr = fmt.communicate(src.encode())
        except BrokenPipeError:
            print("autopep8 not found in PATH")
            return

        if fmt.returncode != 0:
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
