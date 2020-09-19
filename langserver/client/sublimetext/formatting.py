import sublime


def update_edit(view, edit, new_values):
    view.erase_status("lsp_process")
	
    try:
        for val in new_values:
            start_point = view.text_point(
                val["range"]["start"]["line"]-1, val["range"]["start"]["character"])
            end_point = view.text_point(
                val["range"]["end"]["line"]-1, val["range"]["end"]["character"])

            region = sublime.Region(start_point, end_point)
            view.erase(edit, region)
            view.insert(edit, start_point, val["newText"])
    except Exception as e:
        print("error", str(e))