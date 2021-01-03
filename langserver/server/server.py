"""Server module"""

import socket
import logging
from typing import Union, Dict, Any, Callable, Optional, List, Iterable
import rpc
import service.completion_v2 as completion
import service.hover_v2 as hover
import service.formatting_v2 as formatting
import service.serializer as serializer


logger = logging.getLogger("main")
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
SERVER_ERROR_START = -32099
SERVER_ERROR_END = -32000


class ParseError(Exception):
    """Unable to parse message body"""

    ...


class InvalidRequest(Exception):
    """Invalid request"""

    ...


class MethodNotFound(Exception):
    """Command method not found"""

    ...


class InvalidParams(Exception):
    """Invalid params"""

    ...


class InternalError(Exception):
    """Internal error"""

    ...


class ServerErrorStart(Exception):
    """Server error at starting"""

    ...


class ServerErrorEnd(Exception):
    """Server error at shutdown"""

    ...


class Server:
    """Server"""

    def __init__(self, host: str = None, port: int = None) -> None:
        self.host = host
        self.port = port

        self.wait_next = True
        self.command: Dict[str, Callable[[Any], Optional[Any]]] = {}

        self.capability: Dict[str, Any] = {}
        self.workspace: Optional[serializer.WorkspaceParams] = None

    def add_capability(self, capability: Dict[str, Any]) -> None:
        """Add implemented capability"""

        self.capability.update(capability)

    def set_command(self, name: str, function: Callable[[Dict[str, Any]], Any]) -> None:
        """Set command map"""

        self.command[name] = function

    def run_command(
        self, method: str, params: Optional[Dict[str, Any]]
    ) -> Optional[Any]:
        """Execute mapped command"""

        func = self.command.get(method, None)
        if not func:  # for object
            raise MethodNotFound

        results = func(params)
        return results

    def process(self, data: str) -> str:
        """Process request data"""

        logger.debug(data)
        pid: Union[int, str] = -1
        resp_msg: rpc.ResponseMessage

        try:
            req_msg: rpc.RequestMessage = rpc.RequestMessage().parse(data)
            pid = req_msg.id
            results = self.run_command(req_msg.method, req_msg.params)
            err_msg = rpc.ResponseError(code=0)
            resp_msg = rpc.ResponseMessage().create(pid, results, err_msg.error)

        except rpc.ParseError:
            logger.exception("unable parse json", exc_info=True)
            err_msg = rpc.ResponseError(PARSE_ERROR)
            resp_msg = rpc.ResponseMessage().create(pid, None, err_msg.error)

        except rpc.IDInvalidError:
            logger.exception("unable get ID", exc_info=True)
            err_msg = rpc.ResponseError(INVALID_REQUEST)
            resp_msg = rpc.ResponseMessage().create(pid, None, err_msg.error)

        except rpc.MethodInvalidError:
            logger.exception("unable get method", exc_info=True)
            err_msg = rpc.ResponseError(INVALID_REQUEST)
            resp_msg = rpc.ResponseMessage().create(pid, None, err_msg.error)

        except MethodNotFound:
            logger.exception("method not found")
            err_msg = rpc.ResponseError(METHOD_NOT_FOUND)
            logger.debug(err_msg.error)
            resp_msg = rpc.ResponseMessage().create(pid, None, err_msg.error)

        except InvalidParams:
            logger.exception("invalid params")
            err_msg = rpc.ResponseError(INVALID_PARAMS)
            logger.debug(err_msg.error)
            resp_msg = rpc.ResponseMessage().create(pid, None, err_msg.error)

        except InternalError:
            logger.exception("internal error")
            err_msg = rpc.ResponseError(INTERNAL_ERROR)
            logger.debug(err_msg.error)
            resp_msg = rpc.ResponseMessage().create(pid, None, err_msg.error)

        return str(resp_msg)

    def listen(
        self, host: str = None, port: int = None, buffer_size: int = 1024
    ) -> None:
        """Socket listener"""

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:

            host = "127.0.0.1" if host is None else host
            port = 2048 if port is None else port

            sock.bind((host, port))
            sock.listen()
            conn, addr = sock.accept()
            with conn:
                print("Connected by", addr)
                data = b""
                content = ""
                while True:
                    recvdata = conn.recv(buffer_size)
                    data += recvdata
                    try:
                        logger.debug(data)
                        content = rpc.decode(data)
                        break
                    except rpc.ContentIncomplete:
                        continue
                    except rpc.ContentInvalid:
                        break
                    except rpc.ContentOverflow:
                        break

                logger.debug(content)
                result = self.process(content)
                conn.sendall(rpc.encode(result))

    def loop(self, buffer_size: int = 1024) -> None:
        """main loop"""

        while True:
            if self.wait_next:
                self.listen(self.host, self.port, buffer_size)
            else:
                break

    def ping(self, params: Optional[Any] = None) -> Any:
        """Ping test"""

        logger.info("ping test")
        return params

    def initialize(self, params: Optional[Any] = None) -> Dict[str, Any]:
        """Initialize

        Return
            capability
        """

        logger.info("initialize")
        return self.capability

    def exit(self, params: Optional[Any] = None) -> Optional[Any]:
        """Exit services"""

        logger.info("exiting")
        self.wait_next = False
        return None

    def complete(self, params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Fetch completion

        Return:
            completion list object
        """

        try:
            cparam = serializer.CompletionParams.deserialize(params)
            src = cparam.src
            line = cparam.line
            character = cparam.character
            cmpl = completion.Completion(src, line, character)
            logger.debug(
                "line: %s\ncharacter: %s\nsrc +++++ \n%s", line, character, src,
            )

            project = None if not self.workspace else cmpl.project(self.workspace.path)
            i_result: Iterable = cmpl.complete(project=project)
            result: List = list(i_result)  # convert to list
            logger.debug(result)

        except serializer.DeserializeError:
            logger.exception("InvalidParams", exc_info=True)
            raise InvalidParams from None
        except completion.CompletionError:
            logger.exception("CompletionError", exc_info=True)
            raise InternalError from None
        except Exception:
            logger.exception("InternalError", exc_info=True)
            raise InternalError from None

        return result

    def hover(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch help

        Return:
            formatted help object
        """

        try:
            cparam = serializer.HoverParams.deserialize(params)
            src = cparam.src
            line = cparam.line
            character = cparam.character
            hovr = hover.Hover(src, line, character)
            logger.debug(
                "line: %s\ncharacter: %s\nsrc +++++ \n%s", line, character, src,
            )

            project = None if not self.workspace else hovr.project(self.workspace.path)
            result = hovr.hover(project=project)
            logger.debug(result)

        except serializer.DeserializeError:
            logger.exception("InvalidParams", exc_info=True)
            raise InvalidParams from None
        except hover.HoverError:
            logger.exception("InternalError", exc_info=True)
            raise InternalError from None
        except Exception:
            logger.exception("InternalError", exc_info=True)
            raise InternalError from None

        return result

    def change_workspace_config(self, params: Dict[str, Any]) -> Optional[Any]:
        """Update workspace config"""

        try:
            workspace = serializer.WorkspaceParams.deserialize(params)

            self.workspace = workspace
            logger.debug(self.workspace.path)

        except serializer.DeserializeError:
            logger.exception("InvalidParams", exc_info=True)
            raise InvalidParams from None
        except Exception:
            logger.exception("invalid_params", exc_info=True)
            raise InternalError from None

        return None

    def format_(self, params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Format source

        Return:
            changes formatted source object
        """

        try:
            cparam = serializer.FormattingParams.deserialize(params)
            src = cparam.src

            fmt = formatting.Formatting(src)
            logger.debug("src +++++ \n%s", fmt.src)
            i_result: Iterable = fmt.format_code()
            result: List = list(i_result)
            logger.debug(result)

        except serializer.DeserializeError:
            logger.exception("InvalidParams", exc_info=True)
            raise InvalidParams from None
        except formatting.FormattingError:
            logger.exception("InternalError", exc_info=True)
            raise InternalError from None
        except Exception:
            logger.exception("InternalError", exc_info=True)
            raise InternalError from None

        return result


def main() -> None:
    svr = Server(port=2048)
    svr.set_command("exit", svr.exit)
    svr.set_command("ping", svr.ping)
    svr.add_capability(completion.capability())
    svr.add_capability(hover.capability())
    svr.add_capability(formatting.capability())

    svr.set_command("initialize", svr.initialize)
    svr.set_command("textDocument/completion", svr.complete)
    svr.set_command("textDocument/hover", svr.hover)
    svr.set_command("workspace/didChangeConfiguration", svr.change_workspace_config)
    svr.set_command("textDocument/formatting", svr.format_)

    svr.loop()


if __name__ == "__main__":
    main()
