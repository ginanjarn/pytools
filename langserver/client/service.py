import socket
import json
import os
import subprocess
import time
import threading


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
    head = "Content-Length: {}\r\n\r\n".format(len(cnt))
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
        error message if occured"""
    raw_l = raw.decode("ascii").split("\r\n\r\n")
    if len(raw_l) != 2:
        return "", "invalid raw"
    head = raw_l[0]
    head_l = head.split("\r\n")
    if len(head_l) == 0:
        return "", "head not assigned"
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
        return "", "content not valid"
    elif len(body) > cnt_len:
        return None, "content overflow"
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


class Client:
    def __init__(self, python="python", env=None, **kwargs):
        self.python = python
        self.env = env
        self._run_server = kwargs.get("run_server", True)
        # self._server_running = False
        self._server_error = False
        self.req_id = 0
        self._server_activate_retry = 0
        
        # Service block ------------------
        self.completion_capable = False

    def run_server(self):
        def get_server():
            filepath = os.path.abspath(__file__)
            path_list = filepath.split(os.sep)
            serverpath = os.sep.join(path_list[:-2]+["server", "main.py"])
            return serverpath
        run_server_cmd = [self.python, get_server()]
        if os.name == "nt":
            # linux subprocess module does not have STARTUPINFO
            # so only use it if on Windows
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
            server_proc = subprocess.call(run_server_cmd, shell=True,
                             env=self.env, startupinfo=si)
        else:
            server_proc = subprocess.call(run_server_cmd, shell=True, env=self.env)
            # pass

        print(server_proc)
        if server_proc != 0:
            self._server_error = True
            return
        
        self._server_activate_retry += 1

    def _request(self, content: str) -> (str, any):
        """Request message to server
        Params
        ------
        content
            content string
        Returns
        ------
        result
            result string
        error
            if occured, or None"""
        try:
            HOST = '127.0.0.1'  # The server's hostname or IP address
            PORT = 9364        # The port used by the server

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))
                msg = pack(content)
                s.sendall(msg)

                raw = b""
                content, error = "", None
                while True:
                    data = s.recv(1024)
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
            return content, error

            # print('Received', repr(data))
        except ConnectionRefusedError:
            return "", ErrorCodes.serverErrorStart

    def try_running_server(self):
        # don't run if not allowed
        if not self._run_server:
            return
        # run server if not running
        # if self._server_running:
        #     return
        # prevent run if server broken
        if self._server_activate_retry < 5:
            if not self._server_error:
                # running server
                # self.run_server()
                thread = threading.Thread(target=self.run_server)
                thread.setDaemon(True)
                thread.start()
        else:
            # counter >= 5  ---> server broken
            self._server_error = True

    def request(self, method, params=None) -> any:
        try:
            # print(self.req_id)
            msg = {"jsonrpc": "2.0", "id": self.req_id,
                   "method": method, "params": params}

            msg_str = json.dumps(msg)
            result, err = self._request(msg_str)
            if err:
                if err == ErrorCodes.serverErrorStart:
                    if not self._server_error:
                        self.try_running_server()
                        time.sleep(2)
                        result, err = self._request(msg_str)
                    else:
                        return
                else: 
                    if method == "exit":
                        if err["code"] == 0:
                            self.terminate_all_services()
                    return
            result = json.loads(result)
            # print(result)
            if result["id"] != self.req_id:
                return
            self.req_id += 1
            return result["results"]
        except (KeyError, ValueError):
            return None

    def terminate_all_services(self):
        self.completion_capable = False

    def test_conn(self, message=""):
        result, err = self._request(message)
        if err:
            return err
        return result

    def initialize(self):
        try:
            result = self.request("initialize")
            self.completion_capable = result["capabilities"]["capability"]["completionProvider"]["resolveProvider"]
        except(ValueError,KeyError,TypeError):
            pass

    def exit(self):
        try:
            self.request("exit")            
        except(ValueError,KeyError,TypeError):
            pass

    def complete(self, source, line, character):
        if not self.completion_capable:
            return None
        params = {"textDocument": {"uri": source}, "position": {
            "line": line, "character": character}}
        result = self.request("textDocument/completion", params)
        if not result:
            return None
        return result
