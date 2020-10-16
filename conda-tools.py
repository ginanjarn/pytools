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

        self.view.run_command("pytools_set_environment")

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
        s.set("condabin",os.path.join(path,"condabin"))
        env_path_list = [env["prefix"] for env in env_list]
        if prefix not in env_path_list:
            env_list.append(
                {"name": "base", "prefix": prefix, "manager": "conda"})

        envs = os.listdir(os.path.join(path, "envs"))
        if len(envs) > 0:
            envs = [e for e in envs if not e.startswith(".")]
            for env in envs:
                prefix = os.path.join(path, "envs", env)
                if prefix not in env_path_list:
                    env_list.append(
                        {"name": env, "prefix": prefix, "manager": "conda"})
        s.set("environment", env_settings)
        sublime.save_settings("Pytools.sublime-settings")

    def venv_setup(self):
        caption = "Venv path"
        self.view.window().show_input_panel(caption, "", self.scan_venv, None, None)

    def scan_venv(self, path):
        bin_name = "Scripts" if os.name == "nt" else "bin"
        python = "python.exe" if os.name == "nt" else "python"
        if not os.path.isfile(os.path.join(path, bin_name, python)):
            return

        s = sublime.load_settings("Pytools.sublime-settings")
        env_settings = s.get("environment", {})
        try:
            env_list = env_settings["list"]
        except Exception:
            env_settings["list"] = []
            env_list = env_settings["list"]

        prefix = path
        venvname = prefix.split(os.path.sep)[-2] if prefix.endswith(os.path.sep) else prefix.split(os.path.sep)[-1]
        
        env_path_list = [env["prefix"] for env in env_list]
        if prefix not in env_path_list:
            env_list.append(
                {"name": venvname, "prefix": prefix, "manager": "venv"})
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

        def formatname(name):
            fix_len = 16
            name_len = len(name)
            if name_len > fix_len:
                name = name[:fix_len]
            else:
                name += " "*(fix_len-name_len)
            return name

        env_name_l = ["%s : %s" % (formatname(env["name"]), env["prefix"])
                      for env in self.env_list]
        self.view.window().show_quick_panel(env_name_l,
                                            lambda i: self.select_environment(i), flags=sublime.KEEP_OPEN_ON_FOCUS_LOST|sublime.MONOSPACE_FONT)

    def select_environment(self, index):
        if index == -1:
            return

        env_name = self.env_list[index]["name"]
        prefix = self.env_list[index]["prefix"]
        env_manager = self.env_list[index]["manager"]
        env_path = ""
        if env_manager == "conda":
            env_path = os.pathsep.join([prefix,
                                        os.path.join(
                                            prefix, "Library", "mingw-w64", "bin"),
                                        os.path.join(
                                            prefix, "Library", "usr", "bin"),
                                        os.path.join(
                                            prefix, "Library", "bin"),
                                        os.path.join(prefix, "Scripts"),
                                        os.path.join(prefix, "condabin")])
        elif env_manager == "venv":
            env_path = os.pathsep.join([os.path.join(prefix, "Scripts")])

        self.settings.set("python", "python")
        self.settings.set("path", env_path)
        self.settings.set("manager", env_manager)
        self.settings.set("active_environment", env_name)
        sublime.save_settings("Pytools.sublime-settings")

        self.view.run_command("pytools_resetserver")
