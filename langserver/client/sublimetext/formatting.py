import sublime


def update_edit(view, edit, new_values):
    view.erase_status("lsp_process")
    src = view.substr(sublime.Region(0, view.size()))
    newsrc = applyUpdate(src, new_values)
    view.erase(edit, sublime.Region(0, view.size()))
    view.insert(edit,0, newsrc)


def applyUpdate(src, update):
    lines = src.split("\n")
    line_i, update_i = 0, 0
    new_src = []
    pass_insert = False
    len_update = len(update)

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

    return "\n".join(new_src)
