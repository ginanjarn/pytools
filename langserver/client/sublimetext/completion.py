import logging

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


def format_code(data: list) -> any:
    try:
        if not data:
            return None
        parse = [
            ("{}\t{}".format(cmpl["label"], cmpl["kind"]), cmpl["label"])
            for cmpl in data
        ]
        return parse
    except Exception:
        logger.exception("format_code", exc_info=True)
        return
