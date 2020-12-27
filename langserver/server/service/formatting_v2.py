import logging
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

            black_cmd = ["python", "-m", "black", "--diff", "-"]
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
            raise FormattingError from None
        return result

    def extract_updated(self, old_src, update) -> any:
        updates = update.splitlines()
        old_srcs = old_src.split("\n")  # lines separated with "\n"

        text_edit = None

        for index, line in enumerate(updates, start=1):
            if line.startswith("@"):
                if text_edit is not None:
                    _text_edit = text_edit
                    text_edit = None
                    yield _text_edit

                def get_removed_range(args):
                    logger.debug(args)
                    # @@ -a,b ~~~~@@
                    found = re.findall(r"@@\s\-(\d*),(\d*)\s.*@@", args)
                    if found == []:
                        raise ValueError("unable to parse")
                    start = int(found[0][0])
                    # -1,4 => start line 1, show 4 lines
                    end = int(found[0][1]) - 1 + start
                    return start, end

                st, ed = get_removed_range(line)
                logger.debug("start=%s, end=%s", st, ed)
                logger.debug("old_srcs len=%s", len(old_srcs))
                start = {"line": st, "character": 0}
                # fit list zero based index
                end = {
                    "line": ed,
                    "character": len(old_srcs[ed - 1]),
                }
                text_edit = {"range": {"start": start, "end": end}}
            elif line.startswith("-"):
                # ignore removed line
                continue
            else:
                # line start with single character(- or + or <space>)
                line_content = line[1:]
                try:
                    text_edit["newText"] = "\n".join(
                        [text_edit["newText"], line_content]
                    )
                except KeyError:
                    text_edit["newText"] = line_content
                except TypeError:
                    # text_edit is None
                    continue

            # end of line
            if index == len(updates):
                yield text_edit
