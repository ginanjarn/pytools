import socket
import json
from service.completion import Completion, jedi_error  # pylint: disable=import-error


def pack(content: str) -> bytes:
    """Pack string content to binary.
    Header define content property
    Params
    ------
    content: str
        content string
    Returns
    ------
    data: bytes
        bytes binary data"""

    cnt = content.encode("utf-8")
    head = f"Content-Length: {len(cnt)}\r\n\r\n"
    return head.encode("ascii")+cnt


class Encoding:
    """Encoding error value"""
    InvalidData = "invalid data"
    HeaderEmpty = "header empty"
    ContentIncomplete = "content incomplete"
    ContentOverflow = "content overflow"


def unpack(raw: bytes) -> (any, any):
    """Unpack raw data
    Params
    ------
    raw: bytes
        raw data that contain content length
    Returns:
    --------
    content: str
        string content result, or None if content overflow
    error: any
        error message if occured, or None"""
    raw_l = raw.decode("ascii").split("\r\n\r\n")
    if len(raw_l) != 2:
        return "", Encoding.InvalidData
    head = raw_l[0]
    head_l = head.split("\r\n")
    if len(head_l) == 0:
        return "", Encoding.HeaderEmpty
    cnt_len: int = 0
    for row in head_l:
        cols = row.split(": ")
        if len(cols) != 2:
            break
        if cols[0] == "Content-Length":
            cnt_len = int(cols[1])
            break
    body = raw_l[1]
    if len(body) < cnt_len:
        return "", Encoding.ContentIncomplete
    elif len(body) > cnt_len:
        return None, Encoding.ContentOverflow
    else:
        return body, None


class ErrorCodes:
    ParseError = -32700
    InvalidRequest = -32600
    MethodNotFound = -32601
    InvalidParams = -32602
    InternalError = -32603
    serverErrorStart = -32099
    serverErrorEnd = -32000


class Server:
    def __init__(self):
        pass

    def run_service(self):
        HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
        # Port to listen on (non-privileged ports are > 1023)
        PORT = 65432

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            conn, addr = s.accept()
            with conn:
                print('Connected by', addr)
                raw = b""
                content, error = "", None
                while True:
                    data = conn.recv(1024)
                    raw += data
                    result, err = unpack(raw)
                    if err == Encoding.ContentIncomplete:
                        pass
                    elif err == Encoding.ContentOverflow:
                        content = ""
                        error = err
                        break
                    elif err == Encoding.InvalidData:
                        content = ""
                        error = err
                        break
                    elif err == Encoding.HeaderEmpty:
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
                raise Exception(cnt_error)

            data = json.loads(content)
            req_id = data["id"]
            method = data["method"]
            params = data["params"]

            res, err = self._act(method, params)
            if err:
                resp_error = err
            resp_body = res

        except ValueError as e:
            resp_error = {"code": ErrorCodes.InvalidParams, "message": str(e)}
        except Exception as e:
            resp_error = {"code": ErrorCodes.InvalidRequest, "message": str(e)}
        finally:
            # Return
            msg = {"jsonrpc": "2.0", "id": req_id,
                   "results": resp_body, "error": resp_error}
            return json.dumps(msg)

    def _act(self, method, params) -> (any, dict):
        """Act method
        Params
        ------
        method: str
        params: any
            params object
        Returns
        -------
        result: any
            result object or None
        error: dict
            error if occured or None,
            error object contain 'error code' and 'message'"""
        if method == "test_conn":
            # for testing connection purpose. return all received data
            return params

        elif method == "textDocument/completion":
            result, err = self._complete(params)
            return result, {"code": ErrorCodes.InternalError, "message": err}
        else:
            return None, {"code": ErrorCodes.MethodNotFound, "message": method}

    def _complete(self, params) -> (any, any):
        """Do complete
        Params
        ------
        params
            CompletionParams
        Returns:
        -------
        result: list
            completion list
        error"""
        try:
            src = params["textDocument"]["uri"]
            line = params["location"]["line"]
            # jedi line is one based
            line += 1
            character = params["location"]["character"]
            s = Completion(src)
            return s.complete(line, character)
        except ValueError as e:
            return None, str(e)


if __name__ == '__main__':
    s = Server()
    s.run_service()
