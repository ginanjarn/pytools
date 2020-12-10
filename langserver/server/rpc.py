"""RPC encoder - decoder"""

import re
import json
import logging

logger = logging.getLogger("main")
# logger.setLevel(logging.DEBUG)
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


class ParseError(Exception):
    """Unable to parse"""
    pass


class Message:
    def __init__(self,message=None):
        self._message = {"jsonrpc": "2.0"}
        if message is not None:
            self._message.update(message)

    def __str__(self):
        return json.dumps(self._message)

    @classmethod
    def parse(cls, src: str):
        try:
            message = json.loads(src)
        except Exception:
            logger.exception("error parse message")
            raise ParseError
        return cls(message)

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, msg_data: dict):
        if not isinstance(msg_data, dict):
            raise ValueError(
                "required input %s found '%s'" % (type({}) ,type(data)))
        self._message.update(msg_data)


class RequestMessage(Message):
    def __init__(self,message=None):
        super().__init__(message)

    @classmethod
    def create(cls, id, method, params=None, **kwargs):
        message = {}
        message.update({"id": id, "method": method, "params": params})
        message.update(kwargs)
        return cls(message)    

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
    def __init__(self,message=None):
        super().__init__(message)

    @classmethod
    def create(cls, id, results=None, error=None, **kwargs):
        message = {"id": id, "results": results, "error": error}
        message.update(kwargs)
        return cls(message)    

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
    def __init__(self, code, message="", *args, **kwargs):
        self._error = {"code": code, "message": message}
        if len(args)>0:
            for arg in args:
                self._error.update(arg)
        self._error.update(kwargs)

    @classmethod
    def parse(cls, params):
        if not isinstance(params, dict):
            raise ParseError

        code = params.pop("code")
        message = params.pop("message")
        return cls(code, message, params)

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, err_data: dict):
        if not isinstance(err_data, dict):
            raise ValueError(
                "required input <class 'dict'> found '%s'" % type(data))
        self._error.update(err_data)

    @property
    def code(self):
        return self._error.get("code", None)

    @property
    def message(self):
        return self.error.get("message", "")
