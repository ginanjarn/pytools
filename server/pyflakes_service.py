"""handle diagnostic service using pyflakes"""

import logging
import re
from typing import Tuple
from io import StringIO
from pyflakes.api import check
from pyflakes.reporter import Reporter

LOGGER = logging.getLogger(__name__)
# LOGGER.setLevel(logging.DEBUG)
STREAM_HANDLER = logging.StreamHandler()
LOG_TEMPLATE = "%(levelname)s %(asctime)s %(filename)s:%(lineno)s  %(message)s"
STREAM_HANDLER.setFormatter(logging.Formatter(LOG_TEMPLATE))
LOGGER.addHandler(STREAM_HANDLER)

WarningMsg = str
ErrorMsg = str


def publish_diagnostic(source: str, file_name=None) -> Tuple[WarningMsg, ErrorMsg]:
    file_name = file_name or "<stdin>"

    warning_buffer = StringIO()
    error_buffer = StringIO()
    reporter = Reporter(warning_buffer, error_buffer)

    check(source, file_name, reporter)
    LOGGER.debug("warning message: \n%s", warning_buffer.getvalue())
    LOGGER.debug("error message: \n%s", error_buffer.getvalue())

    return (warning_buffer.getvalue(), error_buffer.getvalue())


def diagnostic_to_rpc(messages: Tuple[WarningMsg, ErrorMsg]):
    def build_rpc():
        warning_pattern = re.compile(r"(.*):(\d+):(\d+) (.*)")
        error_pattern = re.compile(r"(.*):(\d+):(\d+): (.*)")

        for line in messages[0].splitlines():
            match = warning_pattern.match(line)
            if match:
                yield {
                    "severity": "warning",
                    "path": match.group(1),
                    "line": int(match.group(2)) - 1,  # editor use 0-based line index
                    "column": int(match.group(3)),
                    "message": match.group(4),
                }

        match = error_pattern.match(messages[1])
        if match:
            yield {
                "severity": "error",
                "path": match.group(1),
                "line": int(match.group(2)) - 1,  # editor use 0-based line index
                "column": int(match.group(3)),
                "message": f"{match.group(4)}\n{messages[1][match.end():]}",
            }

    return list(build_rpc())
