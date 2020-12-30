import sublime
import sublime_plugin
import os
import subprocess
import logging
import re


def get_sysenv():
    s = sublime.load_settings("Pytools.sublime-settings")
    new_paths = s.get("path", "")
    env = os.environ.copy()
    env["PATH"] = new_paths + os.path.pathsep + env["PATH"]
    return env


class PytoolsOpenterminalCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        s = sublime.load_settings("Pytools.sublime-settings")
        work_dir = os.path.dirname(view.file_name())

        if os.name == "nt":
            terminal_cmd = ["C:\\Windows\\System32\\cmd.exe", "/K"]
        else:
            terminal = [
                "gnome-terminal",
                "pantheon-terminal",
                "xfce4-terminal",
                "konsole",
                "lxterminal",
                "mate-terminal",
                "xterm",
            ]
            terminal_cmd = None
            for tm in terminal:
                tm_path = os.path.join("/usr/bin", tm)
                if os.path.isfile(tm_path):
                    terminal_cmd = [tm_path, "-c"]
                    break
            if not terminal_cmd:
                logging.error("terminal not found")
                return

        env_manager = s.get("manager")
        if env_manager:
            conda_bin = s.get("condabin", "")
            conda_bin = os.path.join(conda_bin, "conda")
            env_active = s.get("active_environment")
            if env_manager == "conda":
                activate_cmd = [conda_bin, "activate", env_active]
            elif env_manager == "venv":
                is_conda = False
                home = ""
                with open(os.path.join(env_active, "pyvenv.cfg"), "r") as file:
                    data = file.read()
                    homes = re.findall(r"home = (.*)", data)
                    if len(homes) > 0:
                        home = homes[0]
                        conda = re.match(r".*conda.*", homes[0])
                        if conda:
                            is_conda = True
                bin_name = "Scripts" if os.name == "nt" else "bin"
                if is_conda:
                    activate_cmd = [
                        conda_bin,
                        "activate",
                        home,
                        "&&",
                        os.path.join(env_active, bin_name, "activate"),
                    ]
                else:
                    activate_cmd = [os.path.join(env_active, bin_name, "activate")]

            else:
                activate_cmd = []
                logging.error("environment manager not found")
            proccess_cmd = terminal_cmd + activate_cmd
        else:
            proccess_cmd = terminal_cmd

        subprocess.Popen(proccess_cmd, env=get_sysenv(), cwd=work_dir)

    def is_visible(self):
        view = self.view
        if not view.match_selector(0, "source.python"):
            return False
        return True
