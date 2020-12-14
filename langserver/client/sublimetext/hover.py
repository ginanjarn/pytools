import sublime
from os import path
import logging

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


def goto_definition(view, path_encoded):
    if path_encoded.startswith(":"):
        module_path = path.abspath(view.file_name())+path_encoded
        view.window().open_file(module_path, sublime.ENCODED_POSITION)
    else:
        view.window().open_file(path_encoded, sublime.ENCODED_POSITION)


def show_popup(view, content, location):
    if content is not None:
        view.show_popup(content, sublime.HIDE_ON_MOUSE_MOVE_AWAY | sublime.COOPERATE_WITH_AUTO_COMPLETE, location=location,
                        max_width=800, on_navigate=lambda path_encoded: goto_definition(view, path_encoded))


def format_code(source):
    contents_value = None
    try:
        if not source:
            return
        contents = source["contents"]
        if contents["language"] == "html":
            if contents["value"] == None or contents["value"] == "":
                return None
            contents_value = "<div style=\"margin:.5em\">{}</div>".format(
                contents["value"])
    except Exception:
        logger.exception("format_code", exc_info=True)
    finally:
        return contents_value
