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


def get_params(data: list) -> any:
    try:
        if not data:
            return None

        params_data = []
        for cmpl in data:
            logger.debug(cmpl)
            try:
                params_l = []
                params = cmpl["data"]["params"]
                for param in params:
                    params_l.append(
                        ["%s\t%s" % (param["label"], param["kind"]), "%s=" % (param["label"])])
                params_data.append({"name": cmpl["label"], "data": params_l})
            except Exception:
                # logger.warning("error parsing item", exc_info=True)
                pass

        logger.debug(params_data)
        return params_data

    except Exception:
        logger.error("error parsing params", exc_info=True)
        return