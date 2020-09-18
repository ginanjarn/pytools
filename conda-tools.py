import sublime
import sublime_plugin
import subprocess
import os


def load_settings(key):
    s = sublime.load_settings("Pytools.sublime-settings")
    return s.get(key)


def save_settings(key, value):
    s = sublime.load_settings("Pytools.sublime-settings")
    s.set(key, value)
    sublime.save_settings("Pytools.sublime-settings")


def get_sysenv():
    new_paths = load_settings("path")
    env = os.environ.copy()
    env['PATH'] = new_paths + os.path.pathsep + env['PATH']
    return env


class PytoolsCondasetupCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        condadir = None

        user_env = "USERPROFILE" if os.name == "nt" else "HOME"

        home = os.environ[user_env]
        conda_basedirname = ["anaconda2",
                             "anaconda3", "miniconda2", "miniconda3"]

        for conda in conda_basedirname:
            bin_name = "Scripts" if os.name == "nt" else "bin"
            ext = ".exe" if os.name == "nt" else ""
            default_path = os.path.join(home, conda, bin_name, "conda"+ext)
            if os.path.isfile(default_path):
                condapath = default_path

        if condapath:
            self.setup_conda(condapath)
        else:
            self.input_condadir()

    def input_condadir(self):
        env = os.environ
        user_env = "USERPROFILE" if os.name == "nt" else "HOME"
        prefix = env[user_env]
        self.view.window().show_input_panel("Anaconda install path", prefix,
                                            lambda p: self.parse_conda_input(p), None, None)

    def parse_conda_input(self, condapath):
        bin_name = "Scripts" if os.name == "nt" else "bin"
        ext = ".exe" if os.name == "nt" else ""
        conda_path = os.path.join(condapath, bin_name, "conda"+ext)
        if not os.path.isfile(conda_path):
            return
        self.setup_conda(condapath)

    def setup_conda(self, condapath):
        print(condapath)
        installed_path = os.path.dirname(os.path.dirname(condapath))
        envs = self.load_envs(installed_path)
        save_settings("conda_dir", installed_path)
        save_settings("conda_envs", envs)

        self.view.run_command("pytools_condaenvs")

    def load_envs(self, condadir):
        envs = ["base"]
        try:
            venvs = os.listdir(os.path.join(condadir, "envs"))
            venvs = [v for v in venvs if not v.startswith(".")]
            envs += venvs
        except FileNotFoundError:
            pass
        finally:
            return envs

    def is_visible(self):
        view = self.view
        if not view.match_selector(0, "source.python"):
            return False
        return True


class PytoolsCondaenvsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        envs = load_settings("conda_envs")
        if not envs:
            return
        active_env = load_settings("conda_active")
        try:
            env_i = envs.index(active_env)
        except:
            env_i = 0

        view.window().show_quick_panel(envs, lambda i: self.set_env(
            envs,i), sublime.KEEP_OPEN_ON_FOCUS_LOST, env_i, None)

    def set_env(self, envs, index):
        if index == -1:
            return
        environment = envs[index]
        condadir = load_settings("conda_dir")
        prefix = condadir if environment == "base" else os.path.join(
            condadir, "envs", environment)
        save_settings("conda_active", environment)
        new_paths = os.path.pathsep.join([prefix,
                                          os.path.join(
                                              prefix, "Library", "mingw-w64", "bin"),
                                          os.path.join(
                                              prefix, "Library", "usr", "bin"),
                                          os.path.join(
                                              prefix, "Library", "bin"),
                                          os.path.join(prefix, "Scripts")])
        python = os.path.join(prefix, "python.exe") if os.name == "nt" else os.path.join(
            prefix, "bin", "python")
        save_settings("path", new_paths)
        save_settings("python", python)
        save_settings("conda_active", environment)
        self.view.run_command("pytools_resetserver")

    def is_visible(self):
        view = self.view
        if not view.match_selector(0, "source.python"):
            return False
        return True
