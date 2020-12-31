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
        cparam = serializer.Formatting.deserialize(params)
        self.src = cparam.src

    def format_code(self, src=None):
        try:
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

    def get_removed(self, param):
        rmstr = re.findall(r"@@\s\-(\d*),(\d*)\s.*@@", param)
        if not rmstr:
            raise ValueError("unable to parse")
        start = int(rmstr[0][0])
        end = int(rmstr[0][1]) + start - 1
        return start, end

    def extract_updated(self, old_src, new_src) -> any:
        old_src = old_src.splitlines()
        new_src = new_src.splitlines()
        diff = difflib.unified_diff(old_src, new_src)
        text_edit_list = []
        sub = ()
        index = -1
        for line in diff:
            if line.startswith("@"):
                index += 1
                text_edit = {}

                st, ed = self.get_removed(line)
                start = {"line": st, "character": 0}
                end = {"line": ed, "character": len(old_src[ed - 1])}
                text_edit_list.append(
                    {"range": {"start": start, "end": end}, "newText": ""}
                )
            elif line.startswith("-"):
                continue
            else:
                try:
                    text_edit_list[index]["newText"] = "\n".join(
                        [text_edit_list[index]["newText"], line[1:]]
                    )
                except IndexError:
                    continue
        return text_edit_list
