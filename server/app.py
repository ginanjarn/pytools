"""main app module"""

import json
import logging
import os
import re
import signal
import sys
from socket import socket
from socketserver import TCPServer, BaseServer
from typing import Tuple, Any

LOGGER = logging.getLogger(__name__)
# LOGGER.setLevel(logging.DEBUG)
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


class ContentOverflow(ValueError):
    """content overflow. actual size larger than defined size in header"""


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


class InvalidRequest(ValueError):
    """Request invalid"""


class InvalidParams(ValueError):
    """Params invalid"""


class NotInitialized(ValueError):
    """Project not initialized"""


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

    def shutdown(self, params) -> RPCMessage:
        """shutdown server"""
        LOGGER.info("shutdown")
        self._terminate = True
        return RPCMessage.response()

    def initialize(self, params) -> RPCMessage:
        """initialize project"""
        LOGGER.info("initialize")
        try:
            workspace_path = params["workspace"]["path"]
            os.chdir(workspace_path)
        except Exception:
            workspace_path = ""

        self.project_settings["workspace"] = workspace_path
        LOGGER.debug(f"server capability : {self.server_capability}")
        return RPCMessage.response(result=self.server_capability)

    def change_workspace(self, params) -> RPCMessage:
        LOGGER.info("change workspace")
        try:
            path = params["path"]
        except KeyError as err:
            raise InvalidParams(f"unable get {err}")

        if path == self.project_settings["workspace"]:
            return

        try:
            os.chdir(path)
        except Exception as err:
            return RPCMessage.response(
                error=RPCErrorMessage(code=INPUT_ERROR, message=repr(err))
            )
        else:
            self.project_settings["workspace"] = path
            self.jedi_svc.change_workspace(path)
            LOGGER.debug(self.project_settings["workspace"])
            return RPCMessage.response()

    def exit(self, params) -> RPCMessage:
        """exit project"""
        LOGGER.info("exit")
        self.project_settings = {}

        return RPCMessage.response()

    def document_completion(self, params) -> RPCMessage:
        LOGGER.info("document completion")
        if not self.project_settings:
            raise NotInitialized("project not initialized")

        try:
            source = params["source"]
            row = params["row"]
            column = params["column"]
        except KeyError as err:
            raise InvalidParams(f"unable get {err}")
        except Exception as err:
            raise InvalidParams(f"error: {err}")

        try:
            candidates = self.jedi_svc.complete(source, row, column)
            result = jedi_service.completion_to_rpc(candidates)
        except ValueError as err:
            return RPCMessage.response(
                error=RPCErrorMessage(code=INPUT_ERROR, message=repr(err))
            )
        else:
            return RPCMessage.response(result=result)

    def document_hover(self, params) -> RPCMessage:
        LOGGER.info("document hover")
        if not self.project_settings:
            raise NotInitialized("project not initialized")

        try:
            source = params["source"]
            row = params["row"]
            column = params["column"]
        except KeyError as err:
            raise InvalidParams(f"unable get {err}") from err
        except Exception as err:
            raise InvalidParams(f"error: {err}") from err

        try:
            candidates = self.jedi_svc.hover(source, row, column)
            result = jedi_service.documentation_to_rpc(candidates)
        except ValueError as err:
            return RPCMessage.response(
                error=RPCErrorMessage(code=INPUT_ERROR, message=repr(err))
            )
        else:
            return RPCMessage.response(result=result)

    def document_formatting(self, params) -> RPCMessage:
        LOGGER.info("document formatting")
        if not self.project_settings:
            raise NotInitialized("project not initialized")

        try:
            source = params["source"]
        except KeyError as err:
            raise InvalidParams(f"unable get {err}") from err
        except Exception as err:
            raise InvalidParams(f"error: {err}") from err

        try:
            formatted = black_service.format_code(source)
            result = black_service.changes_to_rpc(source, formatted)
        except black_service.InvalidInput as err:
            return RPCMessage.response(
                error=RPCErrorMessage(code=INPUT_ERROR, message=str(err))
            )
        else:
            return RPCMessage.response(result=result)

    def document_publish_diagnostic(self, params) -> RPCMessage:
        LOGGER.info("document publish diagnostic")
        if not self.project_settings:
            raise NotInitialized("project not initialized")

        try:
            source = params.get("source")
            path = params["path"]
        except KeyError as err:
            raise InvalidParams(f"unable get {err}") from err
        except Exception as err:
            raise InvalidParams(f"error: {err}") from err

        try:
            if source is None:
                with open(path) as file:
                    source = file.read()

            messages = pyflakes_service.publish_diagnostic(source, path)
            result = pyflakes_service.diagnostic_to_rpc(messages)

        except Exception as err:
            return RPCMessage.response(
                error=RPCErrorMessage(code=INTERNAL_ERROR, message=repr(err))
            )
        else:
            return RPCMessage.response(result=result)

    def document_rename(self, params) -> RPCMessage:
        LOGGER.info("document rename")
        raise NotImplementedError("method rename not implemented")

    def handle_request(self, message: RPCMessage) -> RPCMessage:
        try:
            method = message["method"]
            params = message["params"]
        except (KeyError, TypeError) as err:
            raise InvalidRequest("unable get 'method' of 'params'") from err

        try:
            func = self.service_map[method]
        except KeyError as err:
            raise Exception(f"method not found {err}") from err

        return func(params)

    def request_handler(
        self, request: socket, client_address: Tuple[str, int], server: BaseServer
    ):
        """socket server request handler"""

        buffer = []
        buf_size = 2048

        def send_response(message: RPCMessage):
            LOGGER.debug(message)
            if not isinstance(message, RPCMessage):
                raise TypeError("required message type <class 'RPCMessage'>")
            request.sendall(message.to_bytes())

        while True:
            buf = request.recv(buf_size)
            buffer.append(buf)

            try:
                message = RPCMessage.from_bytes(b"".join(buffer))
            except ContentIncomplete:
                continue
            except Exception as err:
                LOGGER.error("parsing error", exc_info=True)
                send_response(
                    RPCMessage.response(
                        error=RPCErrorMessage(INPUT_ERROR, message=str(err))
                    )
                )
                return

            if len(buf) < buf_size:
                break

        response = RPCMessage()
        try:
            result = self.handle_request(message)
        except InvalidRequest as err:
            LOGGER.error("request error", exc_info=True)
            response = RPCMessage.response(error=RPCErrorMessage(INPUT_ERROR, str(err)))
        except InvalidParams as err:
            LOGGER.error("params error", exc_info=True)
            response = RPCMessage.response(error=RPCErrorMessage(PARAM_ERROR, str(err)))
        except NotInitialized as err:
            response = RPCMessage.response(
                error=RPCErrorMessage(NOT_INITIALIZED, str(err))
            )

        except Exception as err:
            LOGGER.error("internal error", exc_info=True)
            response = RPCMessage.response(
                error=RPCErrorMessage(INTERNAL_ERROR, str(err))
            )

        else:
            if result is None:
                response = RPCMessage.response(result="")
            else:
                response = result

        finally:
            send_response(response)

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
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    main()
