import socket
import json
from service.completion import Completion, jedi_error # pylint: disable=import-error


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


def unpack(raw: bytes) -> (str, any):
    """Unpack raw data
    Params
    ------
    raw: bytes
        raw data that contain content length
    Returns:
    --------
    content: str
        string content result
    error: any
        error message if occured"""
    raw_l = raw.decode("ascii").split("\r\n\r\n")
    if len(raw_l) != 2:
        return "", "invalid raw"
    head = raw_l[0]
    head_l = head.split("\r\n")
    if len(head_l) == 0:
        return "", "head not assigned"
    cnt_len: int = 0
    for row in head_l:
        cols = row.split(": ")
        if len(cols) != 2:
            break
        if cols[0] == "Content-Length":
            cnt_len = int(cols[1])
            break
    body = raw_l[1]
    if len(body) != cnt_len:
        return "", "content not valid"
    return body, None


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
                content = ""
                while True:
                    data = conn.recv(1024)
                    result, error = unpack(raw)
                    if not error:
                        content = result
                        break
                    raw += data
                # TODO: do(content)
                result = None
                # TODO: Send result data
                result = pack(result)
                conn.sendall(result)

    def do(self,content:str) -> str:
        data = json.loads(content)
        req_id = data["id"]
        method = data["method"]
        params = data["params"]

        result,error = None,None

        res,err = self._act(method,params)

        if err:
            result = None
            error = {"code":12,"message":err}
        result = res
        
        # Return
        msg = {"jsonrpc":"2.0","id":req_id,"results":result,"error":error}
        return json.dumps(msg)

    def _act(self,method,params) -> (any,any):
        if method == "textDocument/completion":
            result,err = self._complete(params)
            return result,err
        else:
            return None,"Method not found"

    def _complete(self,params) -> (any,any):
        s = Completion(params["uri"])
        return s.complete(params["line"],params["character"])

if __name__ == '__main__':
    s = Server()
    s.run_service()
