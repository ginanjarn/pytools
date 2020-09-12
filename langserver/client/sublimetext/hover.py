import sublime


def show_popup(view, content, location):
    if content:
        view.show_popup(content, sublime.HIDE_ON_MOUSE_MOVE_AWAY, location=location,
                   max_width=450, on_navigate=None)
                   # max_width=450, max_height=None, on_navigate=None, on_hide=None)


def format_code(source):
    try:
        contents = source["contents"]
        if contents["language"] == "html":
            return contents["value"]
    except Exception as e:
        return None
