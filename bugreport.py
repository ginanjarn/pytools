import sublime
import sublime_plugin
import sys
import os


class PytoolsBugreportCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        url = "https://github.com/ginanjarn/pytools/issues/new"

        if sys.platform == 'win32':
            os.startfile(url)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', url])
        else:
            try:
                subprocess.Popen(['xdg-open', url])
            except OSError:
                print('Please open a browser on: '+url)

    def is_visible(self):
        view = self.view
        if not view.match_selector(0, "source.python"):
            return False
        return True
