import sublime
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


def update_edit(view, edit, new_values):
    try:
        if not new_values:
            return
        src = view.substr(sublime.Region(0, view.size()))
        newsrc = applyUpdate(src, new_values)
        view.erase(edit, sublime.Region(0, view.size()))
        view.insert(edit, 0, newsrc)
    except Exception:
        logger.exception("update_edit", exc_info=True)


def applyUpdate(src, update):
    results = None
    try:
        if not update:
            return
        lines = src.split("\n")
        lines = (l for l in lines)
        line_i, update_i = 0, 0
        new_src = []
        pass_insert = False
        len_update = len(update)
        logger.debug(src)
        logger.debug(update)

        for line in lines:
            line_i += 1
            if update_i >= len_update:
                pass_insert = False
            else:
                if line_i == update[update_i]["range"]['start']["line"]:
                    pass_insert = True
                    new_src.append(update[update_i]["newText"])
                    continue
                elif line_i == update[update_i]["range"]['end']["line"]:
                    pass_insert = False
                    update_i += 1
                    continue
                elif update[update_i]["range"]['start']["line"] == update[update_i]["range"]['end']["line"]:
                    pass_insert = False
                    update_i += 1
            if not pass_insert:
                new_src.append(line)
        results = "\n".join(new_src)
        logger.debug(results)
    except Exception:
        logger.exception("applyUpdate", exc_info=True)
    finally:
        return results