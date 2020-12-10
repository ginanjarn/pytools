import socket
import os
import re
import subprocess
import threading
import random
import logging
from . import rpc, serializer

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter(
    '%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


class ServerError(Exception):
    """Server error exception"""
    pass


class NotInitialized(Exception):
    """Server not initialized exception"""
    pass


class ServiceUnavailable(Exception):
    """Service unavailable"""
    pass


class ServerOffline(Exception):
    """Server offline"""
    pass


class InternalError(Exception):
    """Internal error"""
    pass


class Client:

    @staticmethod
    def send_message(data: bytes, buffer_size=1024, host=None, port=None) -> bytes:

        HOST = "127.0.0.1"
        PORT = 2048
        if host is not None:
            HOST = host
        if port is not None:
            PORT = port

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(data)
            data = b""
            while True:
                recvdata = s.recv(buffer_size)
                data += recvdata
                try:
                    content = rpc.decode(data)
                    break
                except rpc.ContentIncomplete:
                    continue
                except rpc.ContentInvalid:
                    break
                except rpc.ContentOverflow:
                    break
        return data

    @staticmethod
    def request(msg, host, port):
        logger.debug(msg)
        emsg = rpc.encode(msg)
        result = Client.send_message(emsg, host=host, port=port)
        result = rpc.decode(result)
        logger.debug(result)
        return result

    @staticmethod
    def run_server(python=None, script=None, env=None):
        python_runtime = "python"
        if python is not None:
            python_runtime = python
        abspath = os.path.abspath(__file__)
        logger.debug(abspath)
        langserver_path = abspath.split(os.sep)[:-2]
        server_script = os.sep.join(langserver_path + ["server", "server.py"])
        if script is not None:
            server_script = script

        run_server_cmd = [python_runtime, server_script]
        logger.debug(run_server_cmd)

        server_proc = None
        try:
            if os.name == "nt":
                # linux subprocess module does not have STARTUPINFO
                # so only use it if on Windows
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
                server_proc = subprocess.Popen(run_server_cmd, stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
                                               env=env, startupinfo=si)
            else:
                server_proc = subprocess.Popen(
                    run_server_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, shell=True, env=env)
        except Exception:
            logger.exception("cannot run_server")

        if server_proc is None:
            raise ServerError

        _, serr = server_proc.communicate()
        if server_proc.returncode != 0:
            logger.error("server error\n%s", str.strip(serr.decode()))
            raise ServerError

    def __init__(self, host=None, port=None):
        self.host = host
        self.port = port

        self.capability = None
        self.server_valid = None

        self.python = None
        self.server_script = None
        self.env = None

        self.cached_workspace = None
        self.server_thread = None

    def _request(self, msg):
        try:
            response = Client.request(msg=msg, host=self.host, port=self.port)
            return response
        except (ConnectionError, ConnectionAbortedError,
                ConnectionRefusedError, ConnectionResetError):
            logger.exception("connection server error", exc_info=False)
            raise ServerOffline
        except Exception:
            logger.exception("internal error", exc_info=True)
            raise InternalError

    def _server_thread(self):
        if self.server_valid:
            try:
                Client.run_server(python=self.python,
                                  script=self.server_script, env=self.env)
            except Exception:
                logger.exception("run_server_thread exception", exc_info=True)
                self.server_valid = False

    def _start_server_thread(self):
        logger.info("running server")

        def make_thread():
            thread = threading.Thread(target=self._server_thread)
            return thread
        if self.server_thread is None:
            self.server_thread = make_thread()
            self.server_thread.start()
        else:
            if not self.server_thread.is_alive():
                self.server_thread = make_thread()
                self.server_thread.start()

    def _init_server(self):
        if self.server_valid is None:
            self.server_valid = True
        else:
            logger.info("server already running")
            return

    def _exit_services(self):
        self.exit()
        self.capability = None
        self.server_valid = None

    @property
    def _req_id(self):
        return random.random()

    def set_python_runtime(self, python=None, env=None):
        self.python = python
        self.env = env
        logger.debug("python = %s, env = %s", self.python,
                     self.env)

    def exit(self):
        msg = rpc.RequestMessage().create(self._req_id, "exit")
        logger.debug(str(msg))
        result = self._request(str(msg))
        logger.debug(result)
        try:
            rmsg = rpc.ResponseMessage.parse(result)
            rerr = rpc.ResponseError.parse(rmsg.error)
            if rerr.code == 0:
                self.capability = None
                self.server_valid = None
        except Exception:
            logger.exception("exit exception", exc_info=True)

    def initialize(self):
        self._init_server()
        try:
            msg = rpc.RequestMessage().create(self._req_id, "initialize")
            logger.debug(str(msg))
            result = self._request(str(msg))
            logger.debug(result)
            rmsg = rpc.ResponseMessage.parse(result)
            results = rmsg.results
            logger.debug(results)
            self.capability = results
        except ServerOffline:
            self._start_server_thread()
        except Exception:
            logger.exception("initialize exception", exc_info=False)

    def ready(self):
        ready = True
        if self.capability is None:
            ready = False
        if not self.server_valid:
            ready = False
        return ready

    def ping(self, data=None):
        msg = rpc.RequestMessage().create(self._req_id, "ping", data)
        logger.debug(str(msg))
        result = self._request(str(msg))
        logger.debug(result)

    def complete(self, source, line, character):
        if self.capability is None:
            raise NotInitialized

        try:
            capable = self.capability["completionProvider"]["resolveProvider"]
            if not capable:
                raise ServiceUnavailable

            params = serializer.Completion.serialize(source, line, character)
            msg = rpc.RequestMessage().create(self._req_id, "textDocument/completion", params)
            logger.debug(str(msg))
            result = self._request(str(msg))
            logger.debug(result)
            rmsg = rpc.ResponseMessage.parse(result)
            results = rmsg.results
            return results
        except ServerOffline:
            self._start_server_thread()
        except Exception:
            logger.exception("complete exception", exc_info=True)

    def hover(self, source, line, character):
        if self.capability is None:
            raise NotInitialized
        try:
            capable = self.capability["hoverProvider"]
            if not capable:
                raise ServiceUnavailable

            params = serializer.Hover.serialize(source, line, character)
            msg = rpc.RequestMessage().create(self._req_id, "textDocument/hover", params)
            logger.debug(str(msg))
            result = self._request(str(msg))
            logger.debug(result)
            rmsg = rpc.ResponseMessage.parse(result)
            results = rmsg.results
            return results
        except ServerOffline:
            self._start_server_thread()
        except Exception:
            logger.exception("hover exception", exc_info=True)

    def set_workspace_config(self, path=""):
        workspace = serializer.Workspace.serialize(path=path)
        if self.cached_workspace != workspace:
            self.cached_workspace = workspace

            params = self.cached_workspace

            msg = rpc.RequestMessage().create(
                self._req_id, "workspace/didChangeConfiguration", params)
            logger.debug(str(msg))
            result = self._request(str(msg))
            logger.debug(result)

    def formatting(self, source):
        if self.capability is None:
            raise NotInitialized

        try:
            capable = self.capability["documentFormattingProvider"]
            if not capable:
                raise ServiceUnavailable
            params = serializer.Formatting.serialize(source)
            msg = rpc.RequestMessage().create(self._req_id, "textDocument/formatting", params)
            logger.debug(str(msg))
            result = self._request(str(msg))
            logger.debug(result)
            rmsg = rpc.ResponseMessage.parse(result)
            results = rmsg.results
            return results
        except ServerOffline:
            self._start_server_thread()
        except Exception:
            logger.exception("formatting exception", exc_info=True)