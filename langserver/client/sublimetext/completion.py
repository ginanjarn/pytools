import logging

logging.basicConfig(format='%(levelname)s: %(asctime)s  %(name)s: %(message)s')
logger = logging.getLogger(__name__)


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