"""RPC encoder - decoder"""

import re
import json
import logging

logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter(
    '%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


def encode(data: str) -> bytes:
    separator = b"\r\n\r\n"
    header = "Content-Length: %s" % (len(data))
    return header.encode("ascii")+separator+data.encode("utf-8")


class ContentInvalid(Exception):
    """Unable resolve content"""
    pass


class ContentIncomplete(Exception):
    """Content length less than defined length"""
    pass


class ContentOverflow(Exception):
    """Content length greater than defined length"""
    pass


def _get_head_and_body(data: bytes) -> (str, str):
    dl = data.split(b"\r\n\r\n")
    if len(dl) != 2:
        raise ContentInvalid
    return (dl[0]).decode("ascii"), dl[1].decode("utf-8")


def _get_contentlength(header: str):
    cl = re.findall(r"Content-Length: (\d*)", header)
    if len(cl) != 1:
        raise ContentInvalid
    return int(cl[0])


def decode(data: bytes) -> str:
    head, body = _get_head_and_body(data)
    clen = _get_contentlength(head)
    if len(body) < clen:
        raise ContentIncomplete
    elif len(body) > clen:
        raise ContentOverflow
    else:
        return body


class Message:
    def __init__(self):
        self._message = {"jsonrpc": "2.0"}

    def __str__(self):
        return json.dumps(self._message)

    def parse(self, src: str):
        self._message = json.loads(src)


class RequestMessage(Message):
    def __init__(self):
        super().__init__()

    def create(self, id, method, params=None, **kwargs):
        self._message.update({"id": id, "method": method, "params": params})
        self._message.update(kwargs)

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, msg_data: dict):
        if type(msg_data) != dict:
            raise ValueError(
                "required input <class 'dict'> found '%s'" % type(data))
        self._message.update(msg_data)

    @property
    def id(self):
        return self._message.get("id", None)

    @property
    def method(self):
        return self._message.get("method", None)

    @property
    def params(self):
        return self._message.get("params", None)


class ResponseMessage(Message):
    def __init__(self):
        super().__init__()

    def create(self, id, results=None, error=None, **kwargs):
        self._message.update({"id": id, "results": results, "error": error})
        self._message.update(kwargs)

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, msg_data: dict):
        if type(msg_data) != dict:
            raise ValueError(
                "required input <class 'dict'> found '%s'" % type(data))
        self._message.update(msg_data)

    @property
    def id(self):
        return self._message.get("id", None)

    @property
    def results(self):
        return self._message.get("results", None)

    @property
    def error(self):
        return self._message.get("error", None)


class ResponseError:
    def __init__(self, code, message="", **kwargs):
        self._error = {"code": code, "message": message}
        self._error.update(kwargs)

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, err_data: dict):
        if type(err_data) != dict:
            raise ValueError(
                "required input <class 'dict'> found '%s'" % type(data))
        self._error.update(err_data)

    @property
    def code(self):
        return self._error.get("code", None)

    @property
    def message(self):
        return self.error.get("message", "")
