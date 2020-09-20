import sublime
import sublime_plugin
import threading
import os
import subprocess


def load_settings(key):
    s = sublime.load_settings("Pytools.sublime-settings")
    return s.get(key)


class PytoolsOpenterminalCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        dirname = os.path.dirname(view.file_name())
        bin_name = "Scripts" if os.name == "nt" else "bin"
        anaconda_dir = load_settings("conda_dir")
        conda_activate = os.path.join(anaconda_dir, bin_name, "activate")
        environment = load_settings("conda_active")

        terminal = "C:\\Windows\\System32\\cmd.exe" if os.name == "nt" else "gnome-terminal"
        cmd = "/K" if os.name == "nt" else "-c"

        process_cmd = [terminal, cmd, conda_activate, "&&",
                       "cd", dirname, "&&", "conda", "activate", environment]
        # print(process_cmd)

        subprocess.Popen(process_cmd)

    def is_visible(self):
        view = self.view
        if not view.match_selector(0, "source.python"):
            return False
        return True