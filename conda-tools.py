import sublime
import sublime_plugin
import subprocess
import os
import re


class PytoolsEnvironmentSetupCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        self.conda_setup()

        manager = ["conda", "venv"]
        self.view.window().show_quick_panel(manager, lambda i: self.select_envmanager(
            manager, i), flags=sublime.KEEP_OPEN_ON_FOCUS_LOST)

    def select_envmanager(self, env_manager, index):
        if index == -1:
            return
        if env_manager[index] == "conda":
            anaconda_install_dir = self.conda_setup()
            if not anaconda_install_dir:
                caption = "Anaconda install path"
                self.view.window().show_input_panel(caption, "", self.scan_conda_envs, None, None)
                return
            self.scan_conda_envs(anaconda_install_dir)

        elif env_manager[index] == "venv":
            self.venv_setup()

        # self.view.run_command("pytools_set_environment")

    def conda_setup(self):
        HOME = "USERPROFILE" if os.name == "nt" else "HOME"
        HOME_path = os.environ[HOME]
        list_homedir = os.listdir(HOME_path)
        anaconda_install_dir = None

        def conda_dir(name):
            conda = None
            found = re.findall(r"\w+conda\w*", name)
            if len(found) > 0:
                conda = found[0]
            return conda

        for name in list_homedir:
            anaconda = conda_dir(name)
            if anaconda:
                anaconda_install_dir = os.path.join(HOME_path, anaconda)
                break
        return anaconda_install_dir
        

    def scan_conda_envs(self, path):
        python = "python.exe" if os.name == "nt" else "bin/python"
        if not os.path.isfile(os.path.join(path, python)):
            print("python not found")
            return

        s = sublime.load_settings("Pytools.sublime-settings")
        env_settings = s.get("environment", {})
        try:
            env_list = env_settings["list"]
        except Exception:
            env_settings["list"] = []
            env_list = env_settings["list"]

        prefix = path
        env_path = os.pathsep.join([prefix,
                                    os.path.join(prefix, "Library",
                                                 "mingw-w64", "bin"),
                                    os.path.join(
                                        prefix, "Library", "usr", "bin"),
                                    os.path.join(prefix, "Library", "bin"),
                                    os.path.join(prefix, "Scripts"),
                                    os.path.join(path, "condabin")])

        env_path_list = [env["path"] for env in env_list]
        if env_path not in env_path_list:
            env_list.append(
                {"name": "base", "path": env_path, "manager": "conda"})

        envs = os.listdir(os.path.join(path, "envs"))
        if len(envs) > 0:
            envs = [e for e in envs if not e.startswith(".")]
            for env in envs:
                prefix = os.path.join(path, "envs", env)
                env_path = os.pathsep.join([prefix,
                                            os.path.join(
                                                prefix, "Library", "mingw-w64", "bin"),
                                            os.path.join(
                                                prefix, "Library", "usr", "bin"),
                                            os.path.join(
                                                prefix, "Library", "bin"),
                                            os.path.join(prefix, "Scripts"),
                                            os.path.join(path, "condabin")])
                if env_path not in env_path_list:
                    env_list.append(
                        {"name": env, "path": env_path, "manager": "conda"})
        s.set("environment", env_settings)
        sublime.save_settings("Pytools.sublime-settings")

    def venv_setup(self):
        caption = "Venv path"
        self.view.window().show_input_panel(caption, "", self.scan_venv, None, None)

    def scan_venv(self, path):
        bin_name = "Scripts" if os.name == "nt" else "bin"
        python = "python.exe" if os.name == "nt" else "python"
        if not os.isfile(os.path.join(path, bin_name, python)):
            return

        s = sublime.load_settings("Pytools.sublime-settings")
        env_settings = s.get("environment", {})
        try:
            env_list = env_settings["list"]
        except Exception:
            env_settings["list"] = []
            env_list = env_settings["list"]

        venvname = path.split(os.path.sep)[-1]
        env_path = os.pathsep.join([os.path.join(path, "Scripts")])

        env_path_list = [env["path"] for env in env_list]
        if env_path not in env_path_list:
            env_list.append(
                {"name": venvname, "path": env_path, "manager": "venv"})
        s.set("environment", env_settings)
        sublime.save_settings("Pytools.sublime-settings")


class PytoolsSetEnvironment(sublime_plugin.TextCommand):
    def run(self, edit):
        self.settings = sublime.load_settings("Pytools.sublime-settings")
        environment_settings = self.settings.get("environment")
        if not environment_settings:
            sublime.error_message("No environment available")
            return

        self.env_list = environment_settings.get("list")
        if not self.env_list:
            sublime.error_message("No environment available")
            return
        env_name_l = ["%s: %s" % (env["manager"], env["name"])
                      for env in self.env_list]
        self.view.window().show_quick_panel(env_name_l,
                                            lambda i: self.select_environment(i), flags=sublime.KEEP_OPEN_ON_FOCUS_LOST)

    def select_environment(self, index):
        if index == -1:
            return

        env_name = self.env_list[index]["name"]
        env_path = self.env_list[index]["path"]
        env_manager = self.env_list[index]["manager"]
        self.settings.set("python", "python")
        self.settings.set("path", env_path)
        self.settings.set("manager", env_manager)
        self.settings.set("active_environment", env_name)
        sublime.save_settings("Pytools.sublime-settings")

        self.view.run_command("pytools_resetserver")