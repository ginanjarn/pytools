import sublime
import sublime_plugin
import threading
import os
import subprocess

def get_sysenv():
    s = sublime.load_settings("Pytools.sublime-settings")
    new_paths = s.get("path","")
    env = os.environ.copy()
    env['PATH'] = new_paths + os.path.pathsep + env['PATH']
    return env

class PytoolsOpenterminalCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        s = sublime.load_settings("Pytools.sublime-settings")
        work_dir = os.path.dirname(view.file_name())
        
        env_path = s.get("path")
        env_manager = s.get("manager")
        env_active = s.get("active_environment")
        if env_manager == "conda":
            activate_cmd = ["conda","activate",env_active]
        elif env_manager == "venv":
            activate_cmd = ["activate"]
        else:
            activate_cmd = []

        if os.name == "nt":
            terminal_cmd = ["C:\\Windows\\System32\\cmd.exe","/K"]
        else:
            terminal_cmd = ["gnome-terminal","-c"]        

        proccess_cmd = terminal_cmd+activate_cmd

        subprocess.Popen(proccess_cmd,env=get_sysenv(),cwd=work_dir)

    def is_visible(self):
        view = self.view
        if not view.match_selector(0, "source.python"):
            return False
        return True