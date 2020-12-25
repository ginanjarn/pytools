import logging


logger = logging.getLogger("formatting")
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter(
    '%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


FORMATTING_CAPABLE = True


try:
    # import autopep8
    import difflib
    import re
    import os
    import black
    import subprocess
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
        except serializer.DeserializeError:
            raise serializer.DeserializeError

    def format_code(self, src=None):
        try:
            if src is not None:
                self.src = src
            # args = autopep8.parse_args(["--diff","-"], apply_config=False)
            # fixed_code = autopep8.fix_code(self.src, args, encoding=None)
            # fixed_code = autopep8.fix_code(self.src)
            # result = self.extract_updated(self.src, fixed_code)
            # logger.debug(result)

            black_cmd = ["python","-m","black","-"]

            env = os.environ.copy()

            if os.name == "nt":
                # linux subprocess module does not have STARTUPINFO
                # so only use it if on Windows
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
                server_proc = subprocess.Popen(black_cmd, stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
                                               env=env, startupinfo=si)
            else:
                server_proc = subprocess.Popen(
                    black_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, shell=True, env=env)

            sout, serr = server_proc.communicate(self.src.encode())
            if server_proc.returncode != 0:
                raise Exception(serr.decode())
            result = self.extract_updated(self.src, sout.decode())

        except Exception:
            raise FormattingError

        return result

    def parse_diff_header(self, param):
        logger.debug(param)
        result = None
        # @@ -a,b +c,d @@
        rst = re.findall(r"@@\s\-(\d*),(\d*)\s\+(\d*),(\d*)\s@@", param)
        # logger.debug(rst)
        if len(rst) == 1:
            result = rst[0]
            result = (int(result[0]), int(result[1])
                      ), (int(result[2]), int(result[3]))
        else:
            rst = re.findall(r"@@\s\-(\d*),(\d*)\s@@", param)
            # logger.debug(rst)
            if len(rst) == 1:
                result = rst[0]
                result = int(result[0]), int(result[1])
        if result is None:
            raise ValueError
        logger.debug(rst)
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
                    sub, _ = self.parse_diff_header(line)
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
        except Exception:
            logger.error("extract_updated", exc_info=True)
