import difflib
formatting_error = None
try:
    import autopep8
except ModuleNotFoundError:
    formatting_error = "autopep8"


class Formatting:
    def __init__(self, source):
        self.src = source

    def format_code(self):
        try:
            # args = autopep8.parse_args(["--diff","-"], apply_config=False)
            # fixed_code = autopep8.fix_code(self.src, args, encoding=None)
            fixed_code = autopep8.fix_code(self.src)
            result = self.extract_updated(self.src, fixed_code)
            return result, None
        except Exception as e:
            return None, str(e)

    def extract_diff_marker(self, mark) -> (any, any):
        sub_start, sub_end = 0, 0
        add_start, add_end = 0, 0
        # @@ -25,6 +25,7 @@
        mark_list = mark.split(" ")  # ["@@","-25,6","+25,7","@@"]
        sub, add = mark_list[1], mark_list[2]  # ["-25,6","+25,7"]
        sub, add = sub[1:], add[1:]  # ["25,6","25,7"]
        sub, add = sub.split(","), add.split(",")  # [("25","6"),("25","7")]
        sub_start, sub_end = int(sub[0]), int(sub[1])   # (25,6))
        add_start, add_end = int(add[0]), int(add[1])   # (25,7)
        return (sub_start, sub_end), (add_start, add_end)   # (25,6),(25,7)

    def extract_updated(self, old_src, new_src) -> any:
        diff = difflib.unified_diff(old_src.splitlines(), new_src.splitlines())

        TextEdit_l = []
        lines = [line for line in diff]
        sub = ()
        index = -1
        line_index = 0

        for line in lines:
            line_index += 1
            if line.startswith("@"):
                index += 1
                TextEdit = {}
                sub, _ = self.extract_diff_marker(line)
                start = {"line": sub[0], "character": len(lines[sub[0]])}
                endline = sub[0]+sub[1]-1
                end = {"line": endline, "character": len(lines[endline])}
                TextEdit["range"] = {"start": start, "end": end}
                TextEdit_l.append(TextEdit)
            elif line.startswith("-"):
                continue
            else:
                try:
                    TextEdit_l[index]["newText"] = "\n".join(
                        [TextEdit_l[index]["newText"], line[1:]])
                except KeyError:
                    TextEdit_l[index]["newText"] = line[1:]
                except IndexError:
                    continue
        return TextEdit_l
