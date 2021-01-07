"""RPC encoder - decoder"""

import re
import json
import logging
from typing import Tuple, Dict, Any, Union, Optional

logger = logging.getLogger("main")
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


def encode(data: str) -> bytes:
    separator = b"\r\n\r\n"
    header = "Content-Length: %s" % (len(data))
    return header.encode("ascii") + separator + data.encode("utf-8")


class ContentInvalid(Exception):
    """Unable resolve content"""

    ...


class ContentIncomplete(Exception):
    """Content length less than defined length"""

    ...


class ContentOverflow(Exception):
    """Content length greater than defined length"""

    ...


class ParseError(Exception):
    """Unable to parse"""

    ...


class IDInvalidError(Exception):
    """Unable to get message ID"""

    ...


class MethodInvalidError(Exception):
    """Unable to get request METHOD"""

    ...


def _get_head_and_body(data: bytes) -> Tuple[str, str]:
    dl = data.split(b"\r\n\r\n")
    if len(dl) != 2:
        raise ContentInvalid
    return (dl[0]).decode("ascii"), dl[1].decode("utf-8")


def _get_contentlength(header: str) -> int:
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
    def __init__(self, message: Dict[str, Any] = None) -> None:
        self._message = {"jsonrpc": "2.0"}
        if message is not None:
            self._message.update(message)

    def __str__(self) -> str:
        return json.dumps(self._message)

    @property
    def message(self) -> Dict[str, Any]:
        return self._message

    @message.setter
    def message(self, msg_data: Dict[str, Any]) -> None:
        self._message.update(msg_data)


class RequestMessage(Message):
    @classmethod
    def parse(cls, src: str) -> "RequestMessage":
        try:
            message = json.loads(src)
        except json.JSONDecodeError:
            logger.exception("error parse message")
            raise ParseError from None
        return cls(message)

    @classmethod
    def create(
        cls,
        msg_id: Union[int, str],
        method: str,
        params: Any = None,
        **kwargs: Optional[Any]
    ) -> "RequestMessage":
        message = {}
        message.update({"id": msg_id, "method": method, "params": params})
        message.update(kwargs)
        return cls(message)

    @property
    def id(self) -> Union[int, str]:
        id_ = self._message.get("id", None)
        if not id_:  # for Union[int, str]
            raise IDInvalidError
        return id_

    @property
    def method(self) -> str:
        method_ = self._message.get("method", None)
        if not method_:  # for str
            raise MethodInvalidError
        return method_

    @property
    def params(self) -> Optional[Any]:
        return self._message.get("params", None)


class ResponseMessage(Message):
    @classmethod
    def parse(cls, src: str) -> "ResponseMessage":
        try:
            message = json.loads(src)
        except json.JSONDecodeError:
            logger.exception("error parse message")
            raise ParseError from None
        return cls(message)

    @classmethod
    def create(
        cls,
        msg_id: Union[int, str],
        results: Optional[Any] = None,
        error: Optional[Any] = None,
        **kwargs: Optional[Any]
    ) -> "ResponseMessage":
        message = {"id": msg_id, "results": results, "error": error}
        message.update(kwargs)
        return cls(message)

    @property
    def id(self) -> Union[int, str]:
        id_ = self._message.get("id", None)
        if not id_:  # for Union[int, str]
            raise IDInvalidError
        return id_

    @property
    def results(self) -> Optional[Union[int, str]]:
        return self._message.get("results", None)

    @property
    def error(self) -> Optional[Any]:
        return self._message.get("error", None)


class ResponseError:
    def __init__(self, code: int, message: str = "", **kwargs: Optional[Any]) -> None:
        self._error = {"code": code, "message": message}
        self._error.update(kwargs)

    @classmethod
    def parse(cls, params: Dict[str, Any]) -> "ResponseError":
        if not isinstance(params, dict):
            raise ParseError

        code: int = params.pop("code")
        message: str = params.pop("message")
        return cls(code, message=message, params=params)

    @property
    def error(self) -> Dict[str, Any]:
        return self._error

    @error.setter
    def error(self, err_data: Dict[str, Any]) -> None:
        self._error.update(err_data)

    @property
    def code(self) -> Union[int, Any]:
        return self._error.get("code", 0)

    @property
    def message(self) -> str:
        return self.error.get("message", "")
