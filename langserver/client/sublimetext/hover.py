from os import path
import logging
import sublime

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


class ContentEmpty(Exception):
    """Content empty"""

    ...

def goto_definition(view, path_encoded):
    if path_encoded.startswith(":"):
        module_path = path.abspath(view.file_name()) + path_encoded
        view.window().open_file(module_path, sublime.ENCODED_POSITION)
    else:
        view.window().open_file(path_encoded, sublime.ENCODED_POSITION)


def show_popup(view, content, location):
    try:
        view.show_popup(
            content,
            sublime.HIDE_ON_MOUSE_MOVE_AWAY | sublime.COOPERATE_WITH_AUTO_COMPLETE,
            location=location,
            max_width=800,
            on_navigate=lambda path_encoded: goto_definition(view, path_encoded),
        )
    except Exception:
        logger.exception("error show popup", exc_info=True)
        raise ValueError("content invalid") from None


def format_code(source):
    try:
        if source["contents"]["language"] == "html":
            content = source["contents"]["value"]

        if content == "":
            raise ContentEmpty

        def wrap(src):
            return '<div style="padding:.5em">%s</div>' % src

        logger.debug(content)
        contents_value = wrap(content)
    except KeyError:
        logger.exception("format_code", exc_info=True)
        raise ValueError("unable to format code") from None
    return contents_value


def show_help(view, content, location):
    try:
        formatted = format_code(content)
        logger.debug(formatted)
        show_popup(view, formatted, location)
    except ContentEmpty:
        pass
    except ValueError:
        logger.exception("error show help", exc_info=True)
