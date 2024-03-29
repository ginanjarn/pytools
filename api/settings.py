"""editor settings"""

from contextlib import contextmanager
import sublime


@contextmanager
def open_settings(base_name, save=False):
    """open settings with context manager"""
    try:
        yield sublime.load_settings(base_name)

    finally:
        if save:
            sublime.save_settings(base_name)


class Settings:
    def __init__(self, base_name):
        self.base_name = base_name

    def get(self, name, default=None):
        with open_settings(self.base_name) as s:
            return s.get(name, default)

    def set(self, name, value):
        with open_settings(self.base_name, True) as s:
            s.set(name, value)

    def add_on_change(self, key, on_change):
        with open_settings(self.base_name) as s:
            s.add_on_change(key, on_change)

    def clear_on_change(self, key):
        with open_settings(self.base_name) as s:
            s.clear_on_change(key)

    def update(self, mappings):
        if not isinstance(mappings, dict):
            raise ValueError("'dict' required")

        with open_settings(self.base_name, True) as s:
            s.update(mappings)



# interpreter
INTERPRETER = "interpreter"

# features
DOCUMENT_COMPLETION = "document_completion"
DOCUMENT_HOVER = "document_hover"
DOCUMENT_FORMATTING = "document_formatting"
DOCUMENT_PUBLISH_DIAGNOSTIC = "document_publish_diagnostic"

# terminal emulator
TERMINAL_EMULATOR = "terminal_emulator"


BASE_NAME = "Pytools.sublime-settings"
BASE_SETTING = Settings(BASE_NAME)
BASE_CHANGE_LISTENER_KEY = "pytools_on_change"
