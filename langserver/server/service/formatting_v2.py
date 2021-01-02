"""Document formatting"""


import logging
import difflib
import re
import os
import subprocess
from typing import Dict, Tuple, Any, List, Iterator, Union


logger = logging.getLogger("formatting")
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


FORMATTING_CAPABLE = True


try:
    import black  # type: ignore
except ModuleNotFoundError:
    FORMATTING_CAPABLE = False


def capability() -> Dict[str, Any]:
    return {"documentFormattingProvider": FORMATTING_CAPABLE}


class FormattingError(Exception):
    """Formatting Error"""

    ...


class Formatting:
    def __init__(self, src: str) -> None:
        self.src = src

    def format_code(self) -> List[Dict[str, Any]]:
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

    def get_removed(self, param: str) -> Tuple[int, int]:
        rmstr = re.findall(r"@@\s\-(\d*),(\d*)\s.*@@", param)
        if not rmstr:
            raise ValueError("unable to parse")
        start = int(rmstr[0][0])
        end = int(rmstr[0][1]) + start - 1
        return start, end

    def extract_updated(self, old_src: str, new_src: str) -> List[Dict[str, Any]]:
        old_srcs: List[str] = old_src.splitlines()
        new_srcs: List[str] = new_src.splitlines()
        diff: Iterator[str] = difflib.unified_diff(old_srcs, new_srcs)
        text_edit_list = []

        # logger.debug(old_srcs)
        # logger.debug(new_srcs)

        index = -1
        for line in diff:
            logger.debug(">>%s", line)
            if line.startswith("@"):
                index += 1

                st, ed = self.get_removed(line)
                start = {"line": st, "character": 0}
                end = {"line": ed, "character": len(old_srcs[ed - 1])}
                text_edit_list.append(
                    {"range": {"start": start, "end": end}, "newText": ""}
                )
            elif line.startswith("-"):
                continue
            else:
                try:
                    cached: Union[str, Any] = text_edit_list[index]["newText"]
                    if not cached:  # for str
                        text_edit_list[index]["newText"] = line[1:]
                    else:
                        text_edit_list[index]["newText"] = "\n".join([cached, line[1:]])
                except IndexError:
                    continue
        logger.debug(text_edit_list)
        return text_edit_list
