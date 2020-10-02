import socket
import json
import argparse
from service import completion, hover, formatting  # pylint: disable=import-error
import logging

logging.basicConfig(format='%(levelname)s: %(asctime)s  %(name)s: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def pack(content: str) -> bytes:
    logger.debug(content)
    cnt = content.encode("utf-8")
    head = f"Content-Length: {len(cnt)}\r\n\r\n"
    result = head.encode("ascii")+cnt
    logger.debug(result)
    return result


class ErrorEncoding:
    """ErrorEncoding value"""
    InvalidData = "invalid data"
    HeaderEmpty = "header empty"
    ContentIncomplete = "content incomplete"
    ContentOverflow = "content overflow"


def unpack(raw: bytes) -> (any, any):
    if not raw:
        logger.error("empty raw data")
        return "", ErrorEncoding.InvalidData
    raw_l = raw.decode("ascii").split("\r\n\r\n")
    if len(raw_l) != 2:
        logger.error("invalid head and body")
        return "", ErrorEncoding.InvalidData
    head = raw_l[0]
    head_l = head.split("\r\n")
    if len(head_l) == 0:
        logger.error("head empty")
        return "", ErrorEncoding.HeaderEmpty
    cnt_len = 0
    for row in head_l:
        cols = row.split(": ")
        if len(cols) != 2:
            logger.warning("invalid key-value field")
            break
        logger.debug("key: %s, value:%s", cols[0], cols[1])
        if cols[0] == "Content-Length":
            cnt_len = int(cols[1])
            logger.info("Content-Length = %s", cnt_len)
            break
    body = raw_l[1]
    if len(body) < cnt_len:
        logger.debug(body)
        logger.info("data incomplete")
        return "", ErrorEncoding.ContentIncomplete
    elif len(body) > cnt_len:
        logger.debug(body)
        logger.error("data larger than Content-Length")
        return None, ErrorEncoding.ContentOverflow
    else:
        logger.debug(body)
        return body, None


class ErrorCodes:
    ParseError = -32700
    InvalidRequest = -32600
    MethodNotFound = -32601
    InvalidParams = -32602
    InternalError = -32603
    serverErrorStart = -32099
    serverErrorEnd = -32000


class ContentInvalidError(Exception):
    """Content invalid exception"""
    pass


class ResposeError:
    """Response error data"""

    def __init__(self, code, message=""):
        self._err_data = {'code': code}
        if message != "":
            self._err_data["message"] = message
        # return err_data

    def error(self):
        return self._err_data


class Server:

    def __init__(self, **kwargs):
        self._run_forever = True
        self.workspace_settings = {}
        self.handler = {}
        self.capability = {}

    def add_handler(self, method: str, handler: any):
        self.handler[method] = handler
        logger.debug(self.handler)

    def add_capability(self, capability, value):
        self.capability[capability] = value
        logger.debug(self.capability)

    def do(self, method, args=None) -> (any, any):
        """Do method
        Params:
        ------
        method: str
            method
        args: any
        Returns
        -------
        result: any | None
        error: any | None
            arguments"""

        try:
            result, error = self.handler[method](args)
            return result, error
        except KeyError as e:
            logger.error("invalid method", exc_info=True)
            return None, ResposeError(code=ErrorCodes.MethodNotFound, message=str(e)).error()

    def run_service(self):
        HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
        # Port to listen on (non-privileged ports are > 1023)
        PORT = 9364

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen()
            while True:
                conn, addr = s.accept()
                with conn:
                    logger.info("connected by %s", addr)
                    raw = b""
                    content, error = "", None
                    while True:
                        data = conn.recv(1024)
                        raw += data
                        result, err = unpack(raw)
                        if err == ErrorEncoding.ContentIncomplete:
                            continue
                        elif err in (ErrorEncoding.ContentOverflow,
                                     ErrorEncoding.InvalidData,
                                     ErrorEncoding.HeaderEmpty):
                            content = ""
                            error = err
                            break
                        else:
                            content = result
                            break

                    # TODO: process(content,error)
                    result_str = self.process(content, error)
                    # TODO: Send result data
                    result = pack(result_str)
                    conn.sendall(result)
                # break if not run forever
                if not self._run_forever:
                    break

    def process(self, content: str, cnt_error: any) -> str:
        """Process request data
        Params
        ------
        content
            string content
        cnt_error
            error if occured"""
        resp_body, resp_error = None, None
        try:
            if cnt_error:
                logger.error("error InvalidData")
                raise ContentInvalidError

            data = json.loads(content)
            req_id = data["id"]
            method = data["method"]
            params = data["params"]

            res, err = self.do(method, params)
            if err:
                resp_error = err
            resp_body = res

        except ValueError as e:
            logger.error(e, exc_info=True)
            resp_error = ResposeError(ErrorCodes.InvalidParams, str(e)).error()
        except ContentInvalidError as e:
            logger.error(e, exc_info=True)
            resp_error = ResposeError(
                ErrorCodes.InvalidRequest, str(e)).error()
        finally:
            # Return
            msg = {"jsonrpc": "2.0", "id": req_id}
            try:
                msg["results"] = resp_body
                msg["error"] = resp_error
                result = json.dumps(msg)
            except ValueError as e:
                logger.error("json dumps error", exc_info=True)
                msg["results"] = None
                msg["error"] = ResposeError(
                    ErrorCodes.InternalError, str(e)).error()
                result = json.dumps(msg)
            logger.debug(result)
            return result

    def initialize(self, params) -> (any, any):
        capability = self.capability
        ServerCapability = {"capability": capability}
        logger.debug(ServerCapability)
        logger.info("initialized")
        return {"capabilities": ServerCapability}, {"retry": False}

    def exit(self, params) -> (any, any):
        self._run_forever = False
        logger.info("terminated")
        return None, ResposeError(code=0).error()

    def change_workspace_config(self, params) -> (any, any):
        try:
            self.workspace_settings = params["DidChangeConfigurationParams"]["settings"]
            logger.debug(self.workspace_settings)
            return None, None
        except ValueError:
            logger.error("error change_workspace_config", exc_info=True)
            return None, ResposeError(code=ErrorCodes.InvalidParams).error()

    def complete(self, params) -> (any, any):
        try:
            src = params["textDocument"]["uri"]
            line = params["position"]["line"]
            # jedi line is one based
            line += 1
            character = params["position"]["character"]
            logger.debug(src)
            logger.debug("line: %s, column: %s", line, character)
            s = completion.Completion(src, settings=self.workspace_settings)
            result, err = s.complete(line, character)
            logger.debug(result)
            if err:
                return None, ResposeError(code=ErrorCodes.InternalError, message=str(err))
            return result, None
        except ValueError as e:
            logger.error("invalid params", exc_info=True)
            return None, ResposeError(code=ErrorCodes.InvalidParams, message=str(e)).error()

    def hover(self, params) -> (any, any):
        try:
            src = params["textDocument"]["uri"]
            line = params["position"]["line"]
            # jedi line is one based
            line += 1
            character = params["position"]["character"]
            logger.debug(src)
            logger.debug("line: %s, column: %s", line, character)
            logger.debug(self.workspace_settings)
            h = hover.Hover(src, settings=self.workspace_settings)
            result, err = h.hover(line, character)
            logger.debug(result)
            if err:
                return None, ResposeError(code=ErrorCodes.InternalError, message=str(err)).error()
            return result, None
        except ValueError as e:
            logger.error("invalid params", exc_info=True)
            return None, str(e)

    def formatting(self, params):
        try:
            src = params["textDocument"]["uri"]
            logger.debug(src)
            f = formatting.Formatting(src)
            result, err = f.format_code()
            logger.debug(result)
            if err:
                return None, ResposeError(code=ErrorCodes.InternalError, message=str(err)).error()
            return result, None
        except ValueError as e:
            logger.error("invalid params", exc_info=True)
            return None, str(e)


def main():
    server = Server()
    server.add_handler("initialize", server.initialize)
    server.add_handler("exit", server.exit)
    server.add_handler("workspace/didChangeConfiguration",
                       server.change_workspace_config)
    server.add_handler("textDocument/completion", server.complete)
    completionCapable = True if not completion.completion_error else False
    server.add_capability("completionProvider", {
                          "resolveProvider": completionCapable})
    server.add_handler("textDocument/hover", server.hover)
    hoverCapable = True if not hover.hover_error else False
    server.add_capability("hoverProvider", hoverCapable)
    server.add_handler("textDocument/formatting", server.formatting)
    formattingCapable = True if not formatting.formatting_error else False
    server.add_capability("documentFormattingProvider", formattingCapable)

    server.run_service()


if __name__ == '__main__':
    main()
