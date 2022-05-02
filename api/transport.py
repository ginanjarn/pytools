import json
import re
import socket


class ContentIncomplete(ValueError):
    """expected size < defined size in header"""


class ContentOverlow(ValueError):
    """expected size > defined size in header"""


class Transport:
    r"""Transport message protocol
    ---------------------------------
    ... Content-Length: <length>\r\n    # header
    ... \r\n                            # separator
    ... content                         # content
    """

    def __init__(self, message: str):
        self.message = message

    def __repr__(self):
        return f"Transport(message='{self.message}')"

    def to_bytes(self):
        content_encoded = self.message.encode()
        header = f"Content-Length: {len(content_encoded)}"
        return b"\r\n\r\n".join([header.encode("ascii"), content_encoded])

    CONTENT_LENGTH_PATTERN = re.compile(r"Content-Length: (\d+)")

    @staticmethod
    def get_content_length(header: str):
        for line in header.splitlines():
            match = Transport.CONTENT_LENGTH_PATTERN.match(line)
            if match:
                return int(match.group(1))
        raise ValueError("Content-Length not found")

    @classmethod
    def from_bytes(cls, buf: bytes):

        try:
            header, body = buf.split(b"\r\n\r\n")
        except Exception:
            raise ValueError("unable get header")

        content_length = cls.get_content_length(header.decode("ascii"))
        expected_length = len(body)

        if expected_length < content_length:
            raise ContentIncomplete(
                f"want {content_length}, expected {expected_length}"
            )

        if expected_length == content_length:
            return cls(body.decode())

        if expected_length > content_length:
            raise ContentOverlow(f"want {content_length}, expected {expected_length}")


def request(message: str) -> str:

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("127.0.0.1", 9005))
        request_msg = Transport(message)
        sock.sendall(request_msg.to_bytes())

        buffer = []
        buf_size = 4096

        while True:
            buf = sock.recv(buf_size)
            buffer.append(buf)

            try:
                response_msg = Transport.from_bytes(b"".join(buffer))
            except ContentIncomplete:
                continue
            if len(buf) < buf_size:
                break

        return response_msg.message


class RPC(dict):
    """RPC base class"""

    def to_str(self):
        """dump to str"""
        return json.dumps(self)

    @classmethod
    def from_str(cls, s):
        """load from str"""
        return cls(json.loads(s))
