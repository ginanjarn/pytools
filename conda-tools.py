import sublime
import sublime_plugin
import subprocess
import os
import re
import logging
import random

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


class InvalidEnvironment(Exception):
    """Invalid python environment. Python binary not found."""
    pass


"""Environment manager"""
CONDA = 0
VENV = 1


class Manager:
    def validate(*args, **kwargs):
        pass

    def make_setting_property(path):
        pass

    def setup(settings, path):
        pass

    def env_list(settings):
        pass

    def remove(settings, env_id):
        pass


class Conda(Manager):
    @staticmethod
    def validate_nt(path):
        if not os.path.isfile(os.path.join(path, "python.exe")):
            logger.debug(os.path.join(path, "python.exe"))
            raise InvalidEnvironment
        return True

    @staticmethod
    def validate_posix(path):
        if not os.path.isfile(os.path.join(path, "bin", "python")):
            raise InvalidEnvironment
        return True

    @staticmethod
    def validate(path):
        if os.name == "nt":
            return Conda.validate_nt(path)
        else:
            return Conda.validate_posix(path)

    @staticmethod
    def browse_envs(path):
        envs = []
        try:
            Conda.validate(path)
            base = path
            envs.append(base)
            for directory in os.listdir(os.path.join(path, "envs")):
                try:
                    envs_path = os.path.join(path, "envs", directory)
                    Conda.validate(envs_path)
                    logger.debug(envs_path)
                    envs.append(envs_path)
                except Exception:
                    logger.debug("environment invalid", exc_info=True)
        except Exception:
            logger.debug("environment invalid", exc_info=True)
        return envs

    @staticmethod
    def make_setting_property(path):
        pid = random.random()
        return {"id": pid, "path": path, "manager": "conda"}

    @staticmethod
    def setup(settings, path):
        envs = Conda.browse_envs(path)
        logger.debug(envs)

        settings.set("condabin", os.path.join(envs[0], "condabin"))

        envs = [Conda.make_setting_property(env) for env in envs]
        try:
            saved = settings.get("conda")
            saved["list"] = envs
            settings.set("conda", saved)
        except Exception:
            settings.set("conda", {"list": envs})

    @staticmethod
    def env_list(settings):
        envs = []
        try:
            envs = settings.get("conda")["list"]
        except Exception:
            logger.debug("no env list")
        return envs

    @staticmethod
    def scan_default_path():
        home_path = os.path.expanduser("~")

        def conda_dir(name):
            found = re.findall(r"\w+conda\w*", name)
            conda = found[0] if len(found) > 0 else None
            return conda

        anaconda = None
        for directory in os.listdir(home_path):
            if conda_dir(directory) is not None:
                anaconda = os.path.join(home_path, directory)
                break
        return anaconda

    @staticmethod
    def remove(settings, env_id):
        try:
            envs = settings.get("conda")["list"]
            matches = list(filter(lambda env: env["id"] == env_id, envs))
            if len(matches) > 0:
                index = envs.index(matches[0])
                envs.pop(index)
            settings.set("conda", {"list": envs})
        except Exception:
            pass


class Venv(Manager):
    @staticmethod
    def validate_nt(path):
        if not os.path.isfile(os.path.join(path, "Scripts", "python.exe")):
            logger.debug(os.path.join(path, "Scripts", "python.exe"))
            raise InvalidEnvironment
        return True

    @staticmethod
    def validate_posix(path):
        if not os.path.isfile(os.path.join(path, "bin", "python")):
            raise InvalidEnvironment
        return True

    @staticmethod
    def validate(path):
        if os.name == "nt":
            return Venv.validate_nt(path)
        else:
            return Venv.validate_posix(path)

    @staticmethod
    def make_setting_property(path):
        pid = random.random()
        return {"id": pid, "path": path, "manager": "venv"}

    @staticmethod
    def setup(settings, path):
        env = None
        try:
            Venv.validate(path)
            env = Venv.make_setting_property(path)
        except Exception:
            logger.debug("setup error", exc_info=True)

        if env is not None:
            venv_stt = settings.get("venv")
            if venv_stt is not None:
                try:
                    venv_stt["list"].append(env)
                except Exception:
                    venv_stt["list"] = [env]
                settings.set("venv", venv_stt)
            else:
                settings.set("venv", {"list": [env]})

    @staticmethod
    def env_list(settings):
        envs = []
        try:
            envs = settings.get("venv")["list"]
        except Exception:
            logger.debug("no env list")
        return envs

    @staticmethod
    def remove(settings, env_id):
        try:
            envs = settings.get("venv")["list"]
            matches = list(filter(lambda env: env["id"] == env_id, envs))
            if len(matches) > 0:
                index = envs.index(matches[0])
                envs.pop(index)
            settings.set("venv", {"list": envs})
        except Exception:
            pass


class Runtime:

    @staticmethod
    def input_pane(window, title, callback, placeholder=""):
        window.show_input_panel(title, "", callback, None, None)

    @staticmethod
    def quick_pane(window, items, callback, default_selected=-1):
        window.show_quick_panel(
            items, callback, flags=sublime.KEEP_OPEN_ON_FOCUS_LOST | sublime.MONOSPACE_FONT)

    @staticmethod
    def setup(manager, settings, path):
        logger.debug(manager)
        envm = {"conda": Conda, "venv": Venv}
        try:
            envm[manager].validate(path)
            envm[manager].setup(settings, path)
        except Exception:
            logger.exception("setup error", exc_info=True)

    @staticmethod
    def env_list(settings):
        env_conda = Conda.env_list(settings)
        env_venv = Venv.env_list(settings)
        return env_conda + env_venv

    @staticmethod
    def remove(settings, env):
        try:
            envm = {"conda": Conda, "venv": Venv}
            envm[env["manager"]].remove(settings, env["id"])
        except Exception:
            pass


class PytoolsEnvironmentSetupCommand(sublime_plugin.WindowCommand):
    def run(self):
        environment = ["conda", "venv"]
        Runtime.quick_pane(self.window, environment, self.init_setup)

    def init_setup(self, index):
        self.manager = ["conda", "venv"][index]
        if index == CONDA:
            path = Conda.scan_default_path()
            self.setup(path)
            if path is None:
                Runtime.input_pane(self.window, "Path", self.setup)
        elif index == VENV:
            Runtime.input_pane(self.window, "Path", self.setup)

    def setup(self, path):
        logger.debug(path)
        logger.debug(self.manager)
        settings = sublime.load_settings("Pytools.sublime-settings")
        Runtime.setup(self.manager, settings, path)
        sublime.save_settings("Pytools.sublime-settings")


class PytoolsSetEnvironment(sublime_plugin.WindowCommand):
    def run(self):
        try:
            self.settings = sublime.load_settings("Pytools.sublime-settings")
            self.envlist = Runtime.env_list(self.settings)
            envsname = ["%s    %s" % (env["manager"], env["path"])
                        for env in self.envlist]

            Runtime.quick_pane(self.window, envsname, self.select_env)
        except Exception:
            logger.exception("set environment error", exc_info=True)

    def select_env(self, index):
        try:
            if index > -1:
                env = self.envlist[index]
                prefix = env["path"]
                self.settings.set("active_environment", prefix)
                env_path = os.pathsep.join([prefix,
                                            os.path.join(
                                                prefix, "Library", "mingw-w64", "bin"),
                                            os.path.join(
                                                prefix, "Library", "usr", "bin"),
                                            os.path.join(
                                                prefix, "Library", "bin"),
                                            os.path.join(prefix, "Scripts")])
                self.set("python", env_path, env["manager"])
        except Exception:
            pass

    def set(self, python, path, manager):
        self.settings.set("python", python)
        self.settings.set("path", path)
        self.settings.set("manager", manager)
        sublime.save_settings("Pytools.sublime-settings")
        self.window.run_command("pytools_shutdownserver")


class PytoolsRemoveEnvironment(sublime_plugin.WindowCommand):
    def run(self):
        self.settings = sublime.load_settings("Pytools.sublime-settings")
        self.envlist = Runtime.env_list(self.settings)
        envsname = [env["path"] for env in self.envlist]

        Runtime.quick_pane(self.window, envsname, self.select_env)

    def select_env(self, index):
        if index > -1:
            logger.debug("change")
            env = self.envlist[index]
            self.remove(env)

    def remove(self, env):
        Runtime.remove(self.settings, env)
        sublime.save_settings("Pytools.sublime-settings")