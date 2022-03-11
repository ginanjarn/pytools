"""handle document formatting with black"""

import logging

from black import FileMode, format_str, DEFAULT_LINE_LENGTH, diff
from black import NothingChanged, InvalidInput

LOGGER = logging.getLogger(__name__)
# LOGGER.setLevel(logging.DEBUG)
STREAM_HANDLER = logging.StreamHandler()
LOG_TEMPLATE = "%(levelname)s %(asctime)s %(filename)s:%(lineno)s  %(message)s"
STREAM_HANDLER.setFormatter(logging.Formatter(LOG_TEMPLATE))
LOGGER.addHandler(STREAM_HANDLER)


def format_code(code: str, **kwargs):
    mode = FileMode(
        target_versions=kwargs.get("versions", set()),
        line_length=kwargs.get("line_length", DEFAULT_LINE_LENGTH),
        is_pyi=kwargs.get("pyi", False),
        string_normalization=kwargs.get("skip_string_normalization", True),
    )
    try:
        formatted = format_str(code, mode=mode)
    except NothingChanged as err:
        LOGGER.debug(repr(err))
        return ""
    else:
        LOGGER.debug("formatted: %s\n", formatted)
        return formatted


def changes_to_rpc(old, new):
    return {"diff": diff(old, new, "Original", "Formatted")}
