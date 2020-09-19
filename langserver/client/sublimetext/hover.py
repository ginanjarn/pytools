import sublime
from os import path

def goto_definition(view, path_encoded):
    if path_encoded.startswith(":"):
        # FIXME: unexpected result
        module_path = path.abspath(view.file_name())+path_encoded
        view.window().open_file(module_path, sublime.ENCODED_POSITION)
        
    else:
        view.window().open_file(path_encoded, sublime.ENCODED_POSITION)


def show_popup(view, content, location):
    if content:
        view.show_popup(content, sublime.HIDE_ON_MOUSE_MOVE_AWAY | sublime.COOPERATE_WITH_AUTO_COMPLETE, location=location,
                        max_width=450, on_navigate=lambda path_encoded: goto_definition(view, path_encoded))
        # max_width=450, max_height=None, on_navigate=None, on_hide=None)


def format_code(source):
    try:
        contents = source["contents"]
        if contents["language"] == "html":
            contents_value = "<div style=\"margin:.5em\">{}</div>".format(contents["value"])
            return contents_value
    except Exception as e:
        return None
