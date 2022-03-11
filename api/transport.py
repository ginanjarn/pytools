import json
import re
import socket


class ContentIncomplete(ValueError):
    """content incomplete, actual size less than defined size in header"""


class ContentOverlow(ValueError):
    """content overflow. actual size larger than defined size in header"""


class TransportMessage:
    r"""Transport message protocol

    message contain header and body

    Header and body separated by \r\n\r\n.
    
    Header must contain 'Content-Length' which value is length body in bytes
    Header format <key>: <value>.
    Multi-line header separated by \r\n.
    """

    def __init__(self, message: str):
        self.message = message

    def __repr__(self):
        return f"TransportMessage(message='{self.message}')"

    def to_bytes(self):
        content_encoded = self.message.encode()
        header = f"Content-Length: {len(content_encoded)}".encode("ascii")
        return b"\r\n\r\n".join([header, content_encoded])

    @classmethod
    def from_bytes(cls, buf: bytes):

        try:
            head, body = buf.split(b"\r\n\r\n")

        except Exception:
            raise ValueError("unable get header")

        _content_length_pattern = re.compile(r"Content-Length: (\d+)")
        _content_length = 0

        for line in head.splitlines():
            match = _content_length_pattern.match(line.decode("ascii"))
            if match:
                _content_length = int(match.group(1))
                # Content-Length found, stop find next
                break

        if not _content_length:
            raise ValueError("unable get 'Content-Length'")

        body_len = len(body)

        if body_len != _content_length:
            if body_len < _content_length:
                raise ContentIncomplete(
                    f"content size invalid, want {_content_length}, expected {body_len}"
                )
            if body_len < _content_length:
                raise ContentOverlow(
                    f"content size invalid, want {_content_length}, expected {body_len}"
                )

        return cls(body.decode())


def request(message: str) -> str:

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("127.0.0.1", 9005))
        tmsg = TransportMessage(message)
        sock.sendall(tmsg.to_bytes())

        buffer = []

        while True:
            msg = sock.recv(1024)
            buffer.append(msg)
            try:
                tmsg = TransportMessage.from_bytes(b"".join(buffer))

            except ContentIncomplete:
                continue

            if len(msg) < 1024:
                break

        return tmsg.message


class RPC(dict):
    """RPC base class"""

    def to_str(self):
        """dump to str"""
        return json.dumps(self)

    @classmethod
    def from_str(cls, s):
        """load from str"""
        return cls(json.loads(s))
