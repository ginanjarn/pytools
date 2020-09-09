import socket
import json
import os
import subprocess


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


class Client:
    def __init__(self, python="python", env=None):
        self.python = python
        self.env = env
        self._server_running = False
        self._server_error = False
        self.req_id = 0

    def _run_server(self):
        def get_server():
            filepath = os.path.abspath(__file__)
            path_list = filepath.split(os.sep)
            serverpath = os.sep.join(path_list[:-2]+["server", "service.py"])
            return serverpath
        run_server_cmd = [self.python, get_server()]
        if os.name == "nt":
            # linux subprocess module does not have STARTUPINFO
            # so only use it if on Windows
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(run_server_cmd, shell=True,
                             env=self.env, startupinfo=si)
        else:
            subprocess.Popen(run_server_cmd, shell=True, env=self.env)

            pass

    def request(self, content: str) -> (str, any):
        try:
            HOST = '127.0.0.1'  # The server's hostname or IP address
            PORT = 65432        # The port used by the server

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))
                msg = pack(content)
                s.sendall(msg)

                raw = b""
                result = ""
                while True:
                    data = s.recv(1024)
                    res, err = unpack(raw)
                    if not err:
                        result = res
                        break
                    raw += data

            return result

            # print('Received', repr(data))
        except ConnectionRefusedError:
            # run server if not running
            self._run_server()
            return ""

    def do(self, method, params) -> any:
        try:
            msg = {"jsonrpc": "2.0", "id": self.req_id,
                   "method": method, "params": params}
            result = self.request(json.dumps(msg))
            if result == "":
                return
            result = json.loads(result)
            if result["id"] != self.req_id:
                return
            self.req_id += 1
            return result["result"]
        except ValueError:
            return None

    def complete(self, source, line, character):
        params = {"uri": source, "position": {
            "line": line, "character": character}}
        result = self.do("textDocument/completion", params)
        if not result:
            return None
        return result
