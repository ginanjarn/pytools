import socket
import json
import argparse
from service.completion import Completion, completion_error  # pylint: disable=import-error
from service.hover import Hover, hover_error  # pylint: disable=import-error


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
    cnt_len = 0
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
    def __init__(self,**kwargs):
        self._test_conn = kwargs.get("test_conn",False)
        self._run_forever = kwargs.get("run_forever",True)

    def run_service(self):
        HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
        # Port to listen on (non-privileged ports are > 1023)
        PORT = 9364

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen()
            while True:
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

                    # return all received data
                    if self._test_conn:
                        result = pack(content)
                        conn.sendall(result)
                        return
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
        if method == "initialize":
            result,err = self.initialize(params)
            return result,err
        
        elif method == "exit":
            result,err = self.exit(params)
            return result,err

        elif method == "textDocument/completion":
            result, err = self.complete(params)
            if err:
                {"code": ErrorCodes.InternalError, "message": err}
            return result, None
        else:
            return None, {"code": ErrorCodes.MethodNotFound, "message": "method not found : {}".format(method)}

    def initialize(self, params) -> (any, any):        
        capability = {}
        if not completion_error:
            capability["completionProvider"]={"resolveProvider":True}
        if not hover_error:
            capability["hoverProvider"]=True

        ServerCapabilities = {"capability":capability}
        return {"capabilities":ServerCapabilities}, {"retry":False}

    def exit(self, params) -> (any,any):
        self._run_forever = False
        return None, {"code": 0}

    def complete(self, params) -> (any, any):
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
            line = params["position"]["line"]
            # jedi line is one based
            line += 1
            character = params["position"]["character"]
            s = Completion(src)
            result, err = s.complete(line,character)
            if err:
                return None,err
            return result, None
        except ValueError as e:
            return None, str(e)

    def hover(self,params) -> (any,any):
        """Do hover
        Params
        ------
        params
            HoverParams
        Returns:
        -------
        result: dict
            documentation formatted with spcific output language
        error"""
        try:
            src = params["textDocument"]["uri"]
            line = params["position"]["line"]
            # jedi line is one based
            line += 1
            character = params["position"]["character"]
            h = Hover(src)
            result, err = h.hover(line,character)
            if err:
                return None, err
            return result, None
        except ValueError as e:
            return None,str(e)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_conn",help="testing connection server",action="store_true")
    parser.add_argument("--test",help="testing mode",action="store_true")
    args = parser.parse_args()
    if args.test_conn:
        s = Server(test_conn=True,run_forever=False)
    elif args.test:
        s = Server(run_forever=False)
    else:
        s = Server(run_forever=True)
    s.run_service()
