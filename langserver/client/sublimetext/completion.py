import logging

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


def format_code(data: list) -> any:
    try:
        parsed = [
            ("%s\t%s" % (completion["label"], completion["kind"]), completion["label"])
            for completion in data
        ]
    except (KeyError, TypeError):
        parsed = None
    logger.debug(parsed)
    return parsed
