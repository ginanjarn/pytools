"""client implementation"""

import logging
import os
import time
import subprocess
from typing import List, Dict, Any
from .transport import request, RPCMessage

LOGGER = logging.getLogger(__name__)
# LOGGER.setLevel(logging.DEBUG)
STREAM_HANDLER = logging.StreamHandler()
LOG_TEMPLATE = "%(levelname)s %(asctime)s %(filename)s:%(lineno)s  %(message)s"
STREAM_HANDLER.setFormatter(logging.Formatter(LOG_TEMPLATE))
LOGGER.addHandler(STREAM_HANDLER)

# RPC error code
INTERNAL_ERROR = 5001
INPUT_ERROR = 5002
METHOD_ERROR = 5004
PARAM_ERROR = 5005
NOT_INITIALIZED = 5006

# server process exit code
EXIT_ADDRESS_IN_USE = 123


class AddressInUse(OSError):
    """socket address in use"""


def run_server(cmd: List[str], workdir: str, envs=None):
    r"""run server with specific environment

    windows command:
      ~\miniconda3\Script\activate envqt && python server

    """

    if os.name == "nt":
        # if on Windows, hide process window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
    else:
        startupinfo = None

    server_proc = subprocess.Popen(
        cmd,
        shell=True,
        cwd=workdir,
        # env=env,
        startupinfo=startupinfo,
    )

    time.sleep(5)
    exit_code = server_proc.poll()
    if exit_code:
        if exit_code == EXIT_ADDRESS_IN_USE:
            raise AddressInUse("socket address in use")
        raise OSError(f"server terminated with exit code {exit_code}")


def shutdown():
    """shutdown server"""
    request(RPCMessage.request(method="shutdown", params=None))


def initialize(workspace_path=None, **kwargs):
    """initialize project"""

    params = {"workspace": {"path": workspace_path}}
    params.update(kwargs)
    response = request(RPCMessage.request(method="initialize", params=params))
    return response


def change_workspace(workspace_path):
    """change workspace path"""

    params = {"path": workspace_path}
    response = request(RPCMessage.request(method="change_workspace", params=params))
    return response


def exit():
    """exit project"""
    request(RPCMessage.request(method="exit", params=None))


def document_completion(source, row, column):
    """document_completion request"""

    params = {"source": source, "row": row, "column": column}
    response = request(RPCMessage.request(method="document_completion", params=params))
    return response


def document_hover(source, row, column):
    """document_hover request"""

    params = {"source": source, "row": row, "column": column}
    response = request(
        RPCMessage.request(method="document_hover", params=params), timeout=10
    )
    return response


def document_formatting(source):
    """document_formatting request"""

    params = {"source": source}
    response = request(RPCMessage.request(method="document_formatting", params=params))
    return response


def document_publish_diagnostic(*, source: str, path: str):
    """document_publish_diagnostic request"""

    params = {"source": source, "path": path}
    response = request(
        RPCMessage.request(method="document_publish_diagnostic", params=params)
    )
    return response


class Session:
    """project session"""

    def __init__(self, config: Dict[str, Any] = None):
        self.active = False
        self.config = config or {}

    def start(self, workspace_path, config: Dict[str, Any] = None):
        config = config or self.config
        try:
            LOGGER.debug("initialize")
            initialize(workspace_path=workspace_path, **self.config)
        except Exception:
            LOGGER.debug("start session failed")
        else:
            self.active = True

    def exit(self):
        try:
            LOGGER.debug("exit")
            exit()
        except Exception:
            LOGGER.debug("exit session")
        finally:
            self.active = False
