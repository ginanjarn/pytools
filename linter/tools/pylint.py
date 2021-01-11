import os
import subprocess
import re
import logging

try:
    # required for typing inspection
    from typing import Any, Iterator, List, Tuple, Optional, Dict
except ImportError:
    ...

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


class CommandError(Exception):
    """Command error"""

    ...


ERROR = 1
WARNING = 2
INFORMATION = 3
HINT = 4


class Pylint:
    """Pylint handler"""

    @staticmethod
    def lint(
        module: str, *args: str, sys_env: "Optional[Dict[str, str]]" = None
    ) -> str:
        try:
            options = "" if not args else " ".join(args)  # type : str
            cmd = ["pylint", "--exit-zero", "--score=n", options, module]

            # default use system env
            env = sys_env if sys_env else os.environ.copy()

            if os.name == "nt":
                # linux subprocess module does not have STARTUPINFO
                # so only use it if on Windows
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
                lint_proc = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    startupinfo=si,
                    bufsize=-1,
                )
            else:
                lint_proc = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    bufsize=-1,
                )
        except OSError as err:
            raise CommandError from err

        sout, serr = lint_proc.communicate()
        if lint_proc.returncode != 0:
            logger.error(serr.decode("utf-8"))
            raise CommandError

        # logger.debug(sout.decode("utf-8"))
        return sout.decode("utf-8")


def lint(
    module: str, env: "Optional[Dict[str, Any]]" = None
) -> "Iterator[Tuple[int, str, str, int, int, str]]":
    """Lint

    Yields:
        tuple (severity, code, module, line, column, message)
    """

    # logger.debug(env)
    template = "@@ {C}: {msg_id}: {module}:{line}:{column}: {msg} @@"
    re_pattern = r"@@ (\w): (\w+): (.*):(\d*):(\d*): (.*) @@\s"
    output = Pylint.lint(
        module, "--msg-template=%s" % (template), sys_env=env
    )  # type : str

    messages = re.findall(re_pattern, output)
    severity_map = {
        "R": HINT,
        "C": INFORMATION,
        "W": WARNING,
        "E": ERROR,
        "F": ERROR,
    }

    for message in messages:
        yield (
            severity_map[message[0]],
            message[1],
            message[2],
            int(message[3]),
            int(message[4]),
            message[5],
        )
