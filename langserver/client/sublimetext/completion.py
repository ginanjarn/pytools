import logging

logging.basicConfig(format='%(levelname)s\t%(module)s: %(lineno)d\t%(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def format_code(data: list) -> any:
    try:
        if not data:
            return None
        parse = [("{}\t{}".format(cmpl["label"], cmpl["kind"]), cmpl["label"])
                 for cmpl in data]
        return parse
    except Exception as e:
        logger.error(e)
        return
