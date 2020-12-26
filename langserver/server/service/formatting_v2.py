import logging
import difflib
import re
import os
import subprocess


logger = logging.getLogger("formatting")
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


FORMATTING_CAPABLE = True


try:
    import black
    from . import serializer
except ModuleNotFoundError:
    FORMATTING_CAPABLE = False


def capability():
    return {"documentFormattingProvider": FORMATTING_CAPABLE}


class FormattingError(Exception):
    """Formatting Error"""

    ...


class Formatting:
    def __init__(self, params):
        try:
            cparam = serializer.Formatting.deserialize(params)
            self.src = cparam.src
        except serializer.DeserializeError as err:
            raise serializer.DeserializeError from err

    def format_code(self, src=None):
        try:
            if src is not None:
                self.src = src

            black_cmd = ["python", "-m", "black", "-"]
            env = os.environ.copy()

            if os.name == "nt":
                # linux subprocess module does not have STARTUPINFO
                # so only use it if on Windows
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
                server_proc = subprocess.Popen(
                    black_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    env=env,
                    startupinfo=si,
                )
            else:
                server_proc = subprocess.Popen(
                    black_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    env=env,
                )

            sout, serr = server_proc.communicate(self.src.encode())
            if server_proc.returncode != 0:
                raise Exception(serr.decode())
            result = self.extract_updated(self.src, sout.decode())

        except Exception as err:
            logger.exception("formatting error", exc_info=True)
            raise FormattingError from err

        return result

    def parse_diff_header(self, param):
        logger.debug(param)
        # @@ -a,b +c,d @@
        rst = re.findall(r"@@\s\-(\d*),(\d*)\s\+(\d*),(\d*)\s@@", param)
        if rst == []:
            raise ValueError("unable to parse")

        logger.debug(rst)
        result = rst[0]
        result = (int(result[0]), int(result[1])), (int(result[2]), int(result[3]))
        logger.debug(result)
        return result

    def extract_updated(self, old_src, new_src) -> any:
        old_src = old_src.splitlines()
        new_src = new_src.splitlines()
        diff = difflib.unified_diff(old_src, new_src)
        text_edit_list = []
        sub = ()
        index = -1
        line_index = 0
        for line in diff:
            line_index += 1
            if line.startswith("@"):
                index += 1
                text_edit = {}
                sub, _ = self.parse_diff_header(line)
                start = {"line": sub[0], "character": 0}
                endline = sub[0] + sub[1] - 1
                end = {"line": endline, "character": len(old_src[endline - 1])}
                text_edit["range"] = {"start": start, "end": end}
                text_edit_list.append(text_edit)
            elif line.startswith("-"):
                continue
            else:
                try:
                    text_edit_list[index]["newText"] = "\n".join(
                        [text_edit_list[index]["newText"], line[1:]]
                    )
                except KeyError:
                    text_edit_list[index]["newText"] = line[1:]
                except IndexError:
                    continue
        return text_edit_list
