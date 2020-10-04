import socket
import json
import os
import re
import subprocess
import threading
import random
import logging

logging.basicConfig(format='%(levelname)s: %(asctime)s  %(name)s: %(message)s')
logger = logging.getLogger(__name__)


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
        error message if occured, or None"""
    if not raw:
        logger.error("empty raw data")
        return "", Encoding.InvalidData
    raw_l = raw.decode("ascii").split("\r\n\r\n")
    if len(raw_l) != 2:
        logger.error("invalid head and body")
        return "", Encoding.InvalidData
    head = raw_l[0]
    logger.debug("header = %s", head)
    try:
        contentLength = re.findall(r"Content-Length: (\d*)", head)
        logger.debug("content length = %s", contentLength)
        if len(contentLength) == 0:
            return "", Encoding.HeaderEmpty
        cnt_len = int(contentLength[0])
        logger.debug("content length = %s", cnt_len)
    except Exception:
        logger.error("invalid header", exc_info=True)
        return "", Encoding.InvalidData

    body = raw_l[1]
    if len(body) < cnt_len:
        logger.debug(body)
        logger.info("data incomplete")
        return "", Encoding.ContentIncomplete
    elif len(body) > cnt_len:
        logger.debug(body)
        logger.error("data larger than Content-Length")
        return None, Encoding.ContentOverflow
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


class Client:
    def __init__(self, python="python", env=None, **kwargs):
        self.python = python
        self.env = env
        self._run_server = kwargs.get("run_server", True)
        self._server_started = False
        self._server_error = False
        self.capabilities = None
        self.config = {}

    def change_python(self, python="python", env=None):
        self.python = python
        self.env = env

        # self.restart_server()

    def run_server(self):
        def get_server():
            filepath = os.path.abspath(__file__)
            path_list = filepath.split(os.sep)
            serverpath = os.sep.join(path_list[:-2]+["server", "main_v2.py"])
            # serverpath = os.sep.join(path_list[:-2]+["server", "main.py"])
            logger.debug(serverpath)
            return serverpath
        run_server_cmd = [self.python, get_server()]
        logger.debug(run_server_cmd)
        if os.name == "nt":
            # linux subprocess module does not have STARTUPINFO
            # so only use it if on Windows
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
            server_proc = subprocess.Popen(run_server_cmd, stdin=subprocess.PIPE,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
                                           env=self.env, startupinfo=si)
        else:
            server_proc = subprocess.Popen(
                run_server_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, shell=True, env=self.env)

        _, serr = server_proc.communicate()
        if server_proc.returncode != 0:
            self._server_error = True
            logger.critical(serr.decode())
            return
        else:
            logger.info("server running")
            return

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
                        logger.debug(content)
                        # print(len(content))
                        # print(content)
                        break
            return content, error

        except (ConnectionRefusedError, ConnectionResetError) as e:
            logger.error(e)
            return "", ErrorCodes.serverErrorStart

    def request(self, method, params=None) -> any:
        try:
            req_id = str(random.random())
            msg = {"jsonrpc": "2.0", "id": req_id,
                   "method": method, "params": params}
            logger.debug("request message = {}".format(msg))
            msg_str = json.dumps(msg)
            result, err = self._request(msg_str)
            if err:
                if err == ErrorCodes.serverErrorStart:
                    # bypass if server not running
                    if method == "exit":
                        self.terminate_all_services()
                        return

                    if self._server_error:
                        return
                    else:
                        if not self._server_started:
                            self._server_started = True
                            thread = threading.Thread(target=self.run_server)
                            thread.setDaemon(True)
                            thread.start()

                        while not self._server_error:
                            result, err = self._request(msg_str)
                            if err:
                                if self._server_error:
                                    break
                                if err == ErrorCodes.serverErrorStart:
                                    continue
                            if result:
                                break

                else:
                    # print("results error", repr(err))
                    logger.error("results error {}".format(repr(err)))
                    return
            result = json.loads(result)
            logger.debug("results = {}".format(result))
            if result["id"] != req_id:
                logger.error("invalid request id, want %s expected %s" %
                             (req_id, result["id"]))
                return

            # terminate on success terminate server
            if method == "exit":
                if result["error"]["code"] == 0:
                    self.terminate_all_services()

            return result["results"]
        except (KeyError, ValueError) as e:
            logging.error(e)
            # print("request error", str(e))
            return None

    def terminate_all_services(self):
        self._server_started = False
        self.capabilities = None
        self.config = {}
        logger.info("server terminated")

    def test_conn(self, message=""):
        result, err = self._request(message)
        if err:
            return err
        return result

    def initialize(self):
        try:
            result = self.request("initialize")
            self.capabilities = {}
            completion = result["capabilities"]["capability"].get(
                "completionProvider")
            if completion:
                self.capabilities["completion_capable"] = completion["resolveProvider"]
            else:
                logger.warning("no completion provider")
            hover = result["capabilities"]["capability"].get("hoverProvider")
            if hover:
                self.capabilities["hover_capable"] = hover
            else:
                logger.warning("no hover provider")
            formatting = result["capabilities"]["capability"].get(
                "documentFormattingProvider")
            if formatting:
                self.capabilities["document_formatting_capable"] = formatting
            else:
                logger.warning("no formatting provider")
            logger.debug(self.capabilities)

        except(ValueError, KeyError, TypeError) as e:
            logger.error(e)
            pass

    def exit(self):
        try:
            self.request("exit")
        except(ValueError, KeyError, TypeError) as e:
            logger.warning(e)
            pass

    def restart_server(self):
        self.exit()
        self.initialize()

    def workspace_config_change(self, config):
        if not self.capabilities:
            logger.info("not initialized")
            return None
        if config == self.config:
            return
        self.config = config
        logger.debug(self.config)
        params = {"DidChangeConfigurationParams": {"settings": config}}
        self.request("workspace/didChangeConfiguration", params)

    def complete(self, source, line, character):
        try:
            if not self.capabilities:
                # print("not initialized")
                logger.error("not initialized")
                return
            if not self.capabilities["completion_capable"]:
                # print("no completion available")
                logger.error("no completion available")
                return
            params = {"textDocument": {"uri": source}, "position": {
                "line": line, "character": character}}
            result = self.request("textDocument/completion", params)
            logger.debug(result)
            if not result:
                return None
            return result
        except Exception as e:
            return None

    def hover(self, source, line, character):
        try:
            if not self.capabilities:
                # print("not initialized")
                logger.error("not initialized")
                return
            if not self.capabilities["hover_capable"]:
                # print("no hover available")
                logger.error("no hover available")
                return
            params = {"textDocument": {"uri": source}, "position": {
                "line": line, "character": character}}
            result = self.request("textDocument/hover", params)
            logger.debug(result)
            if not result:
                return None
            return result
        except Exception as e:
            return None

    def formatting(self, source):
        try:
            if not self.capabilities:
                # print("not initialized")
                logger.error("not initialized")
                return
            if not self.capabilities["document_formatting_capable"]:
                # print("no document_formatting available")
                logger.error("no document_formatting available")
                return
            params = {"textDocument": {"uri": source}}
            result = self.request("textDocument/formatting", params)
            logger.debug(result)
            if not result:
                return None
            return result
        except Exception as e:
            return None
