import difflib
import logging
formatting_error = None
try:
    import autopep8
except ModuleNotFoundError:
    formatting_error = "autopep8"


logging.basicConfig(format='%(levelname)s: %(asctime)s  %(name)s: %(message)s')
logger = logging.getLogger(__name__)


class Formatting:
    def __init__(self, source):
        self.src = source

    def format_code(self):
        try:
            # args = autopep8.parse_args(["--diff","-"], apply_config=False)
            # fixed_code = autopep8.fix_code(self.src, args, encoding=None)
            fixed_code = autopep8.fix_code(self.src)
            result = self.extract_updated(self.src, fixed_code)
            logger.debug(result)
            return result, None
        except Exception as e:
            logger.error(e)
            return None, str(e)

    def extract_diff_marker(self, mark) -> (any, any):
        sub_start, sub_modified = 0, 0
        add_start, add_modified = 0, 0
        # @@ -25,6 +25,7 @@
        mark_list = mark.split(" ")  # ["@@","-25,6","+25,7","@@"]
        sub, add = mark_list[1], mark_list[2]  # ["-25,6","+25,7"]
        sub, add = sub[1:], add[1:]  # ["25,6","25,7"]
        sub, add = sub.split(","), add.split(",")  # [("25","6"),("25","7")]
        if len(sub) == 1:
            sub_start, sub_modified = int(sub[0]), 1   # (25,0)
        elif len(sub) == 2:
            sub_start, sub_modified = int(sub[0]), int(sub[1])   # (25,6)
        else:
            raise Exception("error parsing diff identifier")
        if len(add) == 1:
            add_start, add_modified = int(add[0]), 1   # (25,0)
        elif len(add) == 2:
            add_start, add_modified = int(add[0]), int(add[1])   # (25,7)
        else:
            raise Exception("error parsing diff identifier")
        result = ((sub_start, sub_modified),
                  (add_start, add_modified))   # (25,6),(25,7)
        logger.debug(result)
        return result

    def extract_updated(self, old_src, new_src) -> any:
        try:
            old_src = old_src.splitlines()
            new_src = new_src.splitlines()
            diff = difflib.unified_diff(old_src, new_src)

            TextEdit_l = []
            # lines = [line for line in diff]
            sub = ()
            index = -1
            line_index = 0

            # for line in lines:
            for line in diff:
                line_index += 1
                if line.startswith("@"):
                    index += 1
                    TextEdit = {}
                    sub, _ = self.extract_diff_marker(line)
                    start = {"line": sub[0], "character": 0}
                    endline = sub[0]+sub[1]-1
                    end = {"line": endline, "character": len(
                        old_src[endline - 1])}
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
        except Exception as e:
            logger.error(e)
