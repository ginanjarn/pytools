import json
import re
import socket
from typing import Union


class ContentIncomplete(ValueError):
    """expected size < defined size in header"""


class ContentOverlow(ValueError):
    """expected size > defined size in header"""


class RPCErrorMessage(dict):
    """RPCErrorMessage"""

    def __init__(self, code: int, message: str = "", **kwargs):
        super().__init__({"code": code, "message": message})
        self.update(kwargs)


class RPCMessage(dict):
    """RPCMessage"""

    def to_bytes(self):
        content = json.dumps(self)
        content_encoded = content.encode()
        header = f"Content-Length: {len(content_encoded)}"
        return b"%s\r\n\r\n%s" % (header.encode("ascii"), content_encoded)

    @classmethod
    def request(cls, method, params=None):
        if params is None:
            params = {}
        return cls({"method": method, "params": params})

    @classmethod
    def response(cls, result=None, error=None):
        if error:
            return cls({"error": error})
        return cls({"result": result})

    _content_length_pattern = re.compile(r"Content-Length: (\d+)")

    @staticmethod
    def get_content_length(header):
        for line in header.splitlines():
            match = RPCMessage._content_length_pattern.match(line)
            if match:
                return int(match.group(1))
        raise ValueError("unable get 'Content-Length'")

    @classmethod
    def from_bytes(cls, b: bytes, /):
        try:
            header, content = b.split(b"\r\n\r\n")
        except Exception as err:
            raise ValueError("unable get header") from err
        content_length = cls.get_content_length(header.decode("ascii"))

        expected_length = len(content)
        if expected_length < content_length:
            raise ContentIncomplete(
                f"want {content_length}, expected {expected_length}"
            )
        elif expected_length > content_length:
            raise ContentOverflow(f"want {content_length}, expected {expected_length}")

        try:
            message = json.loads(content.decode())
        except Exception as err:
            LOGGER.debug(content)
            raise ValueError("error parsing message") from err
        return cls(message)


def request(message: Union[bytes, RPCMessage], *, timeout=60) -> RPCMessage:

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("127.0.0.1", 9005))

        if isinstance(message, RPCMessage):
            message = message.to_bytes()

        sock.sendall(message)
        sock.settimeout(timeout)

        buffer = []
        buf_size = 2048

        while True:
            try:
                msg = sock.recv(buf_size)
            except socket.timeout:
                return RPCMessage.response(
                    RPCErrorMessage(code=5000, message="request timedout")
                )

            buffer.append(msg)
            try:
                response = RPCMessage.from_bytes(b"".join(buffer))
            except ContentIncomplete:
                continue

            if len(msg) < buf_size:
                break

        return response
