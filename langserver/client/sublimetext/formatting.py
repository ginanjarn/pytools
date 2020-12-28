import logging
import sublime

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


def update_edit(view, edit, new_values):
    try:
        src = view.substr(sublime.Region(0, view.size()))
        newsrc = apply_update(src, new_values)
        view.erase(edit, sublime.Region(0, view.size()))
        view.insert(edit, 0, newsrc)
    except ValueError:
        logger.exception("update_edit", exc_info=True)


def apply_update(src, updates):
    try:
        srcs = src.split("\n")
        for text_edit in updates:
            start = int(text_edit["range"]["start"]["line"]) - 1
            end = int(text_edit["range"]["end"]["line"])
            del srcs[start:end]
            srcs.insert(start, text_edit["newText"])
        results = "\n".join(srcs)
    except Exception:
        logger.exception("error applying updates", exc_info=True)
        raise ValueError("unable to extract") from None

    logger.debug(results)
    return results
