"""main app module"""

import json
import logging
import os
import re
import signal
import sys
from collections import namedtuple
from socket import socket
from socketserver import TCPServer, BaseServer
from typing import Tuple, Any

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
STREAM_HANDLER = logging.StreamHandler()
LOG_TEMPLATE = "%(levelname)s %(asctime)s %(filename)s:%(lineno)s  %(message)s"
STREAM_HANDLER.setFormatter(logging.Formatter(LOG_TEMPLATE))
LOGGER.addHandler(STREAM_HANDLER)
FILE_HANDLER = logging.FileHandler("server.log")
FILE_HANDLER.setLevel(logging.ERROR)
FILE_HANDLER.setFormatter(logging.Formatter(LOG_TEMPLATE))
LOGGER.addHandler(FILE_HANDLER)

# EXIT CODE
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_OS_ERROR = 123

# RPC error code
INTERNAL_ERROR = 5001
INPUT_ERROR = 5002
METHOD_ERROR = 5004
PARAM_ERROR = 5005
NOT_INITIALIZED = 5006

# Feature capability
DOCUMENT_COMPLETION = True
DOCUMENT_HOVER = True
DOCUMENT_FORMATTING = True
DOCUMENT_PUBLISH_DIAGNOSTIC = True

try:
    import jedi_service
except ImportError:
    DOCUMENT_COMPLETION = False
    DOCUMENT_HOVER = False
try:
    import black_service
except ImportError:
    DOCUMENT_FORMATTING = False
try:
    import pyflakes_service
except ImportError:
    DOCUMENT_PUBLISH_DIAGNOSTIC = False


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


class RPC(dict):
    """RPC base class"""

    def to_str(self):
        """dump to str"""
        return json.dumps(self)

    @classmethod
    def from_str(cls, s):
        """load from str"""
        return cls(json.loads(s))


class ParamError(ValueError):
    """Params invalid"""


class InitializeError(ValueError):
    """Project environment error"""


class ResponseError(dict):
    def __init__(self, *, code, message, **kwargs):
        super().__init__({"code": code, "message": message})
        self.update(kwargs)


class ResponseParams(RPC):
    def __init__(self, *, result: Any = None, error: ResponseError = None):
        if error:
            super().__init__({"error": error})
        else:
            super().__init__({"result": result})


class Server:
    def __init__(self, server_address):
        self.server_address = server_address
        self.tcp_server = TCPServer(server_address, self.request_handler)

        self._terminate = False

        self.server_capability = {
            "document_completion": DOCUMENT_COMPLETION,
            "document_hover": DOCUMENT_HOVER,
            "document_formatting": DOCUMENT_FORMATTING,
            "document_publish_diagnostic": DOCUMENT_PUBLISH_DIAGNOSTIC,
        }

        self.service_map = {
            "ping": self.ping,
            "shutdown": self.shutdown,
            #
            # project
            "initialize": self.initialize,
            "change_workspace": self.change_workspace,
            "exit": self.exit,
            #
            # features
            "document_completion": self.document_completion,
            "document_hover": self.document_hover,
            "document_formatting": self.document_formatting,
            "document_publish_diagnostic": self.document_publish_diagnostic,
        }
        self.project_settings = {}

        self.jedi_svc = jedi_service.Service()

    def serve_forever(self):
        self.tcp_server.serve_forever()

    def ping(self, params) -> Any:
        LOGGER.info("ping")
        return params

    def shutdown(self, params) -> ResponseParams:
        """shutdown server"""
        LOGGER.info("shutdown")
        self._terminate = True
        return ResponseParams()

    def initialize(self, params) -> ResponseParams:
        """initialize project"""
        LOGGER.info("initialize")
        try:
            workspace_path = params["workspace"]["path"]
            os.chdir(workspace_path)
        except Exception:
            workspace_path = ""

        self.project_settings["workspace"] = workspace_path
        LOGGER.debug(f"server capability : {self.server_capability}")
        return ResponseParams(result=self.server_capability)

    def change_workspace(self, params) -> ResponseParams:
        LOGGER.info("change workspace")
        try:
            path = params["path"]
        except KeyError as err:
            raise ParamError(f"unable get {err}")

        if path == self.project_settings["workspace"]:
            return

        try:
            os.chdir(path)
        except Exception as err:
            return ResponseParams(
                error=ResponseError(code=INPUT_ERROR, message=repr(err))
            )
        else:
            self.project_settings["workspace"] = path
            self.jedi_svc.change_workspace(path)
            LOGGER.debug(self.project_settings["workspace"])
            return ResponseParams()

    def exit(self, params) -> ResponseParams:
        """exit project"""
        LOGGER.info("exit")
        self.project_settings = {}

        return ResponseParams()

    def document_completion(self, params) -> ResponseParams:
        LOGGER.info("document completion")
        if not self.project_settings:
            raise InitializeError("project not initialized")

        try:
            source = params["source"]
            row = params["row"]
            column = params["column"]
        except KeyError as err:
            raise ParamError(f"unable get {err}")
        except Exception as err:
            raise ParamError(f"error: {err}")

        try:
            candidates = self.jedi_svc.complete(source, row, column)
            result = jedi_service.completion_to_rpc(candidates)
        except ValueError as err:
            return ResponseParams(
                error=ResponseError(code=INPUT_ERROR, message=repr(err))
            )
        else:
            return ResponseParams(result=result)

    def document_hover(self, params):
        LOGGER.info("document hover")
        if not self.project_settings:
            raise InitializeError("project not initialized")

        try:
            source = params["source"]
            row = params["row"]
            column = params["column"]
        except KeyError as err:
            raise ParamError(f"unable get {err}") from err
        except Exception as err:
            raise ParamError(f"error: {err}") from err

        try:
            candidates = self.jedi_svc.hover(source, row, column)
            result = jedi_service.documentation_to_rpc(candidates)
        except ValueError as err:
            return ResponseParams(
                error=ResponseError(code=INPUT_ERROR, message=repr(err))
            )
        else:
            return ResponseParams(result=result)

    def document_formatting(self, params):
        LOGGER.info("document formatting")
        if not self.project_settings:
            raise InitializeError("project not initialized")

        try:
            source = params["source"]
        except KeyError as err:
            raise ParamError(f"unable get {err}") from err
        except Exception as err:
            raise ParamError(f"error: {err}") from err

        try:
            formatted = black_service.format_code(source)
            result = black_service.changes_to_rpc(source, formatted)
        except black_service.InvalidInput as err:
            return ResponseParams(
                error=ResponseError(code=INPUT_ERROR, message=str(err))
            )
        else:
            return ResponseParams(result=result)

    def document_publish_diagnostic(self, params):
        LOGGER.info("document publish diagnostic")
        if not self.project_settings:
            raise InitializeError("project not initialized")

        try:
            source = params.get("source")
            path = params["path"]
        except KeyError as err:
            raise ParamError(f"unable get {err}") from err
        except Exception as err:
            raise ParamError(f"error: {err}") from err

        try:
            if not source:
                with open(path) as file:
                    source = file.read()

            messages = pyflakes_service.publish_diagnostic(source, path)
            result = pyflakes_service.diagnostic_to_rpc(messages)

        except Exception as err:
            return ResponseParams(
                error=ResponseError(code=INTERNAL_ERROR, message=repr(err))
            )
        else:
            return ResponseParams(result=result)

    def document_rename(self, params):
        LOGGER.info("document rename")
        raise NotImplementedError("method rename not implemented")

    def handle_message(self, message: str) -> str:
        """handle request message"""
        try:
            rpc = RPC.from_str(message)
        except json.JSONDecodeError as err:
            # raise ValueError(f"invalid message, encoding error '{err}'") from err
            return ResponseParams(
                error=ResponseError(
                    code=INPUT_ERROR, message=f"json decoding error {repr(err)}"
                )
            ).to_str()

        try:
            method = rpc["method"]
            params = rpc["params"]
        except KeyError as err:
            # raise ValueError(f"invalid message, unable get '{err}'") from err
            return ResponseParams(
                error=ResponseError(
                    code=INPUT_ERROR, message=f"invalid RPC, unable get {err}"
                )
            ).to_str()

        try:
            func = self.service_map[method]
        except KeyError as err:
            # raise ValueError(f"method not found '{err}'") from err
            return ResponseParams(
                error=ResponseError(
                    code=METHOD_ERROR, message=f"method not found {err}"
                )
            ).to_str()

        try:
            LOGGER.debug(f"method: {method}, params: {params}")
            result = func(params)
            message = result.to_str()

            LOGGER.debug("valid result : %s", message)

        except ParamError as err:
            message = ResponseParams(
                error=ResponseError(code=PARAM_ERROR, message=repr(err))
            ).to_str()

        except InitializeError as err:
            message = ResponseParams(
                error=ResponseError(code=NOT_INITIALIZED, message=repr(err))
            ).to_str()

        except Exception as err:
            message = ResponseParams(
                error=ResponseError(code=INTERNAL_ERROR, message=repr(err))
            ).to_str()
            LOGGER.debug("error result : %s", message)

        return message

    def request_handler(
        self, request: socket, client_address: Tuple[str, int], server: BaseServer
    ):
        """socket server request handler"""

        buffer = []
        result_message = b""

        while True:
            msg = request.recv(1024)
            buffer.append(msg)
            try:
                tmsg = TransportMessage.from_bytes(b"".join(buffer))

            except ContentIncomplete:
                continue

            if len(msg) < 1024:
                break

        try:
            result_message = TransportMessage(
                self.handle_message(tmsg.message)
            ).to_bytes()

        except Exception as err:
            # result_message = TransportMessage(repr(err)).to_bytes()
            result_message = TransportMessage(
                ResponseParams(
                    error=ResponseError(code=INTERNAL_ERROR, message=repr(err))
                ).to_str()
            ).to_bytes()
        finally:
            LOGGER.debug("result_message : %s", result_message)
            request.sendall(result_message)

            if self._terminate:
                sys.exit(EXIT_SUCCESS)


def terminate(*args):
    LOGGER.debug(f"terminate {args}")
    sys.exit(EXIT_SUCCESS)


def main():
    try:
        signal.signal(signal.SIGTERM, terminate)

        try:
            server = Server(("localhost", 9005))
            print(f"running server server at {server.server_address}")
            server.serve_forever()

        except OSError as err:
            print(f"os error: {err}")
            sys.exit(EXIT_OS_ERROR)

    except KeyboardInterrupt as err:
        print(f"KeyboardInterrupt {err}")
        pass

    except Exception as err:
        LOGGER.error(f"application error {err}", exc_info=True)


if __name__ == "__main__":
    main()
