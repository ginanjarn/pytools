import socket
import json
import os
import re
import subprocess
import threading
import random
import logging
import rpc
import serializer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
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
    def request(msg,host,port):
        try:
            logger.debug(msg)
            emsg = rpc.encode(msg)
            result = Client.send_message(emsg,host=host,port=port)
            result = rpc.decode(result)
            logger.debug(result)
            return result
        except (ConnectionError,ConnectionAbortedError,
            ConnectionRefusedError,ConnectionResetError):
            logger.exception("connection server error",exc_info=True)
        except Exception:
            logger.exception("internal error",exc_info=True)


    def __init__(self,host=None,port=None):
        self.host = host
        self.port = port

        self.capability = None


    def _request(self,msg):
        return Client.request(msg=msg,host=self.host,port=self.port)

    def exit(self):
        msg = rpc.RequestMessage().create(12, "exit")
        logger.debug(str(msg))
        result = self._request(str(msg))
        logger.debug(result)
        try:
            rmsg = rpc.ResponseMessage.parse(result)
            rerr = rpc.ResponseError.parse(rmsg.error)
            if rerr.code == 0:
                self.capability = None
        except Exception:
            logger.exception("exit exception",exc_info=True)    
    
    def initialize(self):
        msg = rpc.RequestMessage().create(12, "initialize")
        logger.debug(str(msg))
        result = self._request(str(msg))
        logger.debug(result)
        try:
            rmsg = rpc.ResponseMessage.parse(result)
            results = rmsg.results
            logger.debug(results)
            self.capability = results
        except Exception:
            logger.exception("initialize exception", exc_info=True)    

    
    def ping(self,data=None):
        msg = rpc.RequestMessage().create(12, "ping", data)
        logger.debug(str(msg))
        result = self._request(str(msg))
        logger.debug(result)
    
    
    def complete(self,source, line, character):
        if self.capability is None:
            raise NotInitialized

        try:
            capable = self.capability["completionProvider"]["resolveProvider"]
            if not capable:
                raise ServiceUnavailable
        
            params = serializer.Completion.serialize(source,line,character)
            msg = rpc.RequestMessage().create(25, "textDocument/completion", params)
            logger.debug(str(msg))
            result = self._request(str(msg))
            logger.debug(result)
            rmsg = rpc.ResponseMessage.parse(result)
            results = rmsg.results
            return results
        except Exception:
            logger.exception("complete exception", exc_info=True)
    
    def hover(self,source, line, character):
        if self.capability is None:
            raise NotInitialized
        try:
            capable = self.capability["hoverProvider"]
            if not capable:
                raise ServiceUnavailable

            params = serializer.Hover.serialize(source,line,character)
            msg = rpc.RequestMessage().create(25, "textDocument/hover", params)
            logger.debug(str(msg))
            result = self._request(str(msg))
            logger.debug(result)
            rmsg = rpc.ResponseMessage.parse(result)
            results = rmsg.results
            return results
        except Exception:
            logger.exception("hover exception",exc_info=True)
    
    def set_workspace_config(self, path=""):
        params = serializer.Workspace.serialize(path=path)
        msg = rpc.RequestMessage().create(40,"workspace/didChangeConfiguration",params)
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
            msg = rpc.RequestMessage().create(25, "textDocument/formatting", params)
            logger.debug(str(msg))
            result = self._request(str(msg))
            logger.debug(result)
            rmsg = rpc.ResponseMessage.parse(result)
            results = rmsg.results
            return results
        except Exception:
            logger.exception("formatting exception", exc_info=True)