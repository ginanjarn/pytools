import socket
import rpc
import logging
import json


logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter(
    '%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
SERVER_ERROR_START = -32099
SERVER_ERROR_END = -32000


class ParseError(Exception):
    pass


class InvalidRequest(Exception):
    pass


class MethodNotFound(Exception):
    pass


class InvalidParams(Exception):
    pass


class InternalError(Exception):
    pass


class ServerErrorStart(Exception):
    pass


class ServerErrorEnd(Exception):
    pass


class Server:
    def __init__(self):
        self.wait_next = True
        self.command = {}

    def listen(self, buffer_size=1024):
        HOST = "127.0.0.1"
        PORT = 1205

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            conn, addr = s.accept()
            with conn:
                print('Connected by', addr)
                data = b""
                content = ""
                while True:
                    recvdata = conn.recv(buffer_size)
                    data += recvdata
                    try:
                        logger.debug(data)
                        content = rpc.decode(data)
                        break
                    except rpc.ContentIncomplete:
                        continue
                    except rpc.ContentInvalid:
                        break
                    except rpc.ContentOverflow:
                        break

                logger.debug(content)
                result = self.process(content)
                conn.sendall(rpc.encode(result))
                # conn.sendall(rpc.encode(content))

    def loop(self, buffer_size=1024):
        while True:
            if self.wait_next:
                self.listen(buffer_size)
            else:
                break

    def set_command(self, name, function):
        self.command[name] = function

    def run_command(self, method, *args):
        results = None
        try:
            logger.debug("run_command %s %s", method, *args)
            results = self.command[method](*args)
        except KeyError:
            raise MethodNotFound
        finally:
            return results

    def parse_request(self, msg: str):
        logger.debug(msg)
        rm = rpc.RequestMessage()
        rm.parse(msg)
        logger.debug(rm)
        return rm

    def process(self, data: str):
        logger.debug(data)
        req_msg = None
        resp_msg = rpc.ResponseMessage()

        results = None
        err_msg = rpc.ResponseError(code=0)
        pid = None

        try:
            req_msg = self.parse_request(data)
            pid = req_msg.id
        except json.JSONDecodeError:
            logger.exception("unable parse json", exc_info=True)
            err = rpc.ResponseError(PARSE_ERROR)
            err_msg.error = err.error

            resp_msg.create(pid, results, err_msg.error)
            return str(resp_msg)

        if req_msg is not None:
            try:
                results = self.run_command(req_msg.method, req_msg.params)
            except MethodNotFound:
                err = rpc.ResponseError(METHOD_NOT_FOUND)
                err_msg.message = err.error
                logger.exception("method not found")
            finally:
                resp_msg.create(pid, results, err_msg.error)
                return str(resp_msg)

    def exit(self, *arg):
        logger.info("exiting")
        self.wait_next = False
        return None

    def ping(self, *args):
        logger.info("ping test")
        return args


def main():
    svr = Server()
    svr.set_command("exit", svr.exit)
    svr.set_command("ping", svr.ping)

    svr.loop()


if __name__ == '__main__':
    main()