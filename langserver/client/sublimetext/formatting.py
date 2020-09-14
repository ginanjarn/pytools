import sublime

def update_edit(view,edit,new_values):
	for val in new_values:
		start_point = view.text_point(val["start"]["line"],val["start"]["character"])
		end_point = view.text_point(val["end"]["line"],val["end"]["character"])
		region = sublime.Region(start_point,end_point)
		view.erase(edit,region)