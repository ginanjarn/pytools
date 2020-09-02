import sublime
import sublime_plugin
import threading
import os
import subprocess


def print_to_outputpane(msg):
    win = sublime.active_window()
    panel = win.create_output_panel("panel")
    panel.run_command("append", {"characters": msg})
    win.run_command('show_panel', {"panel": "output.panel"})


def hide_outputpane():
    win = sublime.active_window()
    win.run_command('hide_panel', {"panel": "output.panel"})


def load_settings(key):
    s = sublime.load_settings("Pytools.sublime-settings")
    return s.get(key)


def get_sysenv():
    new_paths = load_settings("path")
    env = os.environ.copy()
    env['PATH'] = new_paths + os.path.pathsep + env['PATH']
    return env


class PytoolsLintCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        dirname = os.path.dirname(view.file_name())

        thread = threading.Thread(
            target=self.do_lint, args=(dirname, view.file_name()))
        thread.start()

    def format_output(self, lines):
        if lines == "":
            return ""
        lines = lines.split("\n")
        lines = [line.strip() for line in lines]
        return "\n".join(lines)

    def do_lint(self, work_dir, file_name):
        lint_process_cmd = ["pylint", file_name]
        lint_env = get_sysenv()
        if os.name == "nt":
            # linux subprocess module does not have STARTUPINFO
            # so only use it if on Windows
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
            lint_proc = subprocess.Popen(lint_process_cmd,shell=True,
                                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=lint_env, startupinfo=si, bufsize=-1)
        else:
            lint_proc = subprocess.Popen(lint_process_cmd,shell=True,
                                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=lint_env, bufsize=-1)

        sout, serr = lint_proc.communicate()

        if lint_proc.returncode == 0:
            hide_outputpane()
        elif lint_proc.returncode == 1:
            print(self.format_output(serr.decode()))
        else:
            print_to_outputpane(self.format_output(sout.decode()))