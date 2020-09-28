import sublime
import sublime_plugin
import subprocess
import os


class PytoolsEnvironmentSetupCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        manager = ["conda", "venv"]
        self.view.window().show_quick_panel(manager, lambda i: self.select_envmanager(
            manager, i), flags=sublime.KEEP_OPEN_ON_FOCUS_LOST)

    def select_envmanager(self, env_manager, index):
        if index == -1:
            return
        if env_manager[index] == "conda":
            self.conda_setup()
        elif env_manager[index] == "venv":
            self.venv_setup()

    def conda_setup(self):
        HOME = "USERPROFILE" if os.name == "nt" else "HOME"
        HOME_path = os.environ[HOME]
        anaconda_dir = ["anaconda2", "anaconda3", "miniconda2", "miniconda3"]
        list_homedir = os.listdir(HOME_path)
        anaconda_install_dir = None
        for anaconda in anaconda_dir:
            if anaconda in list_homedir:
                anaconda_install_dir = os.path.join(HOME_path, anaconda)
                break
        if not anaconda_install_dir:
            caption = "Anaconda install path"
            self.view.window().show_input_panel(caption, "", scan_conda_envs, None, None)
            return
        self.scan_conda_envs(anaconda_install_dir)

    def scan_conda_envs(self, path):
        python = "python.exe" if os.name == "nt" else "bin/python"
        if not os.path.isfile(os.path.join(path, python)):
            print("python not found")
            return

        conda_l = []
        prefix = path
        env_path = os.pathsep.join([prefix,
                                    os.path.join(prefix, "Library",
                                                 "mingw-w64", "bin"),
                                    os.path.join(
                                        prefix, "Library", "usr", "bin"),
                                    os.path.join(prefix, "Library", "bin"),
                                    os.path.join(prefix, "Scripts"),
                                    os.path.join(path, "condabin")])
        conda_l.append({"name": "base", "path": env_path, "manager": "conda"})

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
                conda_l.append(
                    {"name": env, "path": env_path, "manager": "conda"})

        s = sublime.load_settings("Pytools.sublime-settings")
        environment_settings = s.get("environment")

        if not environment_settings:
            s.set("environment", {"list": conda_l})
            sublime.save_settings("Pytools.sublime-settings")
            return

        env_list = environment_settings.get("list")
        if not env_list:
            environment_settings["list"] = conda_l
        else:
            environment_settings["list"].extend(conda_l)
        s.set("environment", environment_settings)
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
        venvname = path.split(os.path.sep)[-1]

        env_path = os.pathsep.join([os.path.join(path, "Scripts")])
        environment_settings = s.get("environment")

        if not environment_settings:
            venv = {
                "list": [{"name": venvname, "path": env_path, "manager": "venv"}]}
            s.set("environment", venv)
            sublime.save_settings("Pytools.sublime-settings")
            return
        env_list = python_settings.get("list")
        if not env_list:
            environment_settings["list"] = [
                {"name": venvname, "path": env_path, "manager": "venv"}]
        else:
            environment_settings["list"].append(
                {"name": venvname, "path": env_path, "manager": "venv"})
        s.set("environment", python_settings)
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