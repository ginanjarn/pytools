import os
import subprocess
import re
import logging


logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter(
    '%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


class CommandError(Exception):
    """Command error"""
    pass


ERROR = 1
WARNING = 2
INFORMATION = 3
HINT = 4


class PylintFormatter:
    """Pylint output formatter helper"""

    template = "@@ {C}: {msg_id}: {module}:{line}:{column}: {msg} @@"
    re_pattern = r"@@ (\w): (\w+): (.*):(\d*):(\d*): (.*) @@\s"

    @staticmethod
    def parse_output(message):
        """parse pylint output message

        Args:
            message: str

        Yield:
            dict formatted message. keys = ["severity", "code",
                            "module", "line", "column", "message"]"""
        
        def convert_severity(severity):
            level = {"R": HINT, "C": INFORMATION,
                     "W": WARNING, "E": ERROR, "F": ERROR}
            return level[severity]

        def parse_message(msg):
            msg = {
                "severity": convert_severity(msg[0]),
                "code": msg[1], "module": msg[2], "line": int(msg[3]),
                "column": int(msg[4]), "message": msg[5]
            }
            return msg

        lines = re.findall(PylintFormatter.re_pattern, message)
        for line in lines:
            yield parse_message(line)


class Pylint:
    def __init__(self, path, env=None):
        if env is None:
            env = os.environ.copy()
        self.path = path
        self.env = env

    def lint(self, options=None, **kwargs):
        """lint command

        Args:
            option: list
            template: pylint output message template

        Return
            raw string: message"""

        try:
            if options is None:
                options = []
            options += ["--exit-zero", "--score=n"]

            if "template" in kwargs:
                options += ["--msg-template=%s" % kwargs["template"]]

            cmd = ["pylint"] + options + [self.path]

            logger.debug(cmd)
            if os.name == "nt":
                # linux subprocess module does not have STARTUPINFO
                # so only use it if on Windows
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
                lint_proc = subprocess.Popen(cmd, shell=True,
                                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE, env=self.env, startupinfo=si,
                                             bufsize=-1)
            else:
                lint_proc = subprocess.Popen(cmd, shell=True,
                                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE, env=self.env, bufsize=-1)
        except Exception:
            raise CommandError

        sout, serr = lint_proc.communicate()
        logger.debug("exit = %s", lint_proc.returncode)
        if lint_proc.returncode != 0:
            logger.debug(serr.decode().replace(os.linesep, "\n"))
            raise CommandError

        logger.debug(sout.decode().replace(os.linesep, "\n"))
        return sout.decode()


# if __name__ == '__main__':
#     pl = Pylint("diagnostic.py")
#     try:
#         rt = pl.lint(template=PylintFormatter.template)
#         # logger.debug(rt)
#         res = PylintFormatter.parse_output(rt)
#         logger.debug(list(res))
#     except Exception:
#         logger.exception("Pylint", exc_info=True)