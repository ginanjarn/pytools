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
            target=self.do_lint, args=(view, dirname, view.file_name()))
        thread.start()

    def do_lint(self, view, work_dir, file_name):
        lint_process_cmd = ["pylint", "--disable=all",
                            "--enable=F,E,unreachable,duplicate-key,unnecessary-semicolon,global-variable-not-assigned,unused-variable,binary-op-exception,bad-format-string,anomalous-backslash-in-string,bad-open-mode",
                            "--msg-template='{C}::{msg_id}::{line}::{column}::{msg}::{module}'",
                            "--exit-zero", "--score=no", file_name]
        lint_env = get_sysenv()
        if os.name == "nt":
            # linux subprocess module does not have STARTUPINFO
            # so only use it if on Windows
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
            lint_proc = subprocess.Popen(lint_process_cmd, shell=True,
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=lint_env, startupinfo=si, bufsize=-1)
        else:
            lint_proc = subprocess.Popen(lint_process_cmd, shell=True,
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=lint_env, bufsize=-1)

        sout, serr = lint_proc.communicate()
        if lint_proc.returncode != 0:
            print(serr.decode())
        else:
            print(sout.decode())
            res, err = self.format_output(sout.decode())
            if err:
                print(err)
                return
            # print(res)
            self.mark_view(view, res)

    def format_output(self, data):
        try:
            diagnostic_l = data.split("\r\n")

            """
            [R]efactor for a “good practice” metric violation
            [C]onvention for coding standard violation
            [W]arning for stylistic problems, or minor programming issues
            [E]rror for important programming issues (i.e. most probably bug)
            [F]atal for errors which prevented further processing
            """
            severity = {"E": 1, "F": 1, "W": 2, "C": 3, "R": 4}

            Diagnostics = []

            for diagnostic in diagnostic_l:
                # "--msg-template='{C}:{msg_id}:{line}:{column}:{msg}:{module}'",
                try:
                    msg_l = diagnostic.split("::")
                    svrt = severity[msg_l[0]]
                    range_ = {"start": {"line": int(msg_l[2]), "character": int(msg_l[3])},
                              "end": {"line": int(msg_l[2]), "character": int(msg_l[3])}}
                    msg = "{}:{}:{} {}".format(
                        msg_l[5], msg_l[2], msg_l[3], msg_l[4])

                    Diagnostic = {"range": range_,
                                  "severity": svrt, "message": msg}
                    Diagnostics.append(Diagnostic)

                except (KeyError, IndexError):
                    continue

            return {"diagnostics": Diagnostics}, None
        except Exception as e:
            return None, str(e)

    def mark_view(self, view, diagnostics):
        # Key
        key_err = "pytools-lint-err"
        key_warn = "pytools-lint-warn"

        # Clear regions
        view.erase_regions(key_err)
        view.erase_regions(key_warn)

        # Holder
        errors = []
        regions_err, regions_warn = [], []
        error, warning = 0, 0

        for diagnostic in diagnostics["diagnostics"]:
            line, row = int(diagnostic["range"]["start"]["line"]) - \
                1, int(diagnostic["range"]["start"]["character"])
            point = view.text_point(line, row)
            if diagnostic["severity"] == 1:
                regions_err.append(view.line(point))
                errors.append("❌ {}".format(diagnostic["message"]))
                error += 1
            elif diagnostic["severity"] == 2:
                regions_warn.append(view.line(point))
                errors.append("⚠ {}".format(diagnostic["message"]))
                warning += 1

        # Mark view
        view.add_regions(key=key_err, regions=regions_err, scope="invalid.illegal", icon="",
                         flags=sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SOLID_UNDERLINE)
        view.add_regions(key=key_warn, regions=regions_warn, scope="invalid.deprecated", icon="",
                         flags=sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SOLID_UNDERLINE)

        print_to_outputpane("\n".join(errors))