import socket
import subprocess
import sys
import threading
import os


class Client:
    def __init__(self, python_path=None, script_path=None, sys_env=None):
        self.python_path = python_path
        self.script_path = script_path
        self.sys_env = sys_env
        self.terminate = False
        self.server_error = False
        self.next = True

    def run_server(self):
        python_path = self.python_path if self.python_path != None else "python"
        filedir = os.path.dirname(__file__)
        script_path = self.script_path if self.script_path != None else os.path.join(
            filedir, "server.py")
        try:
            rescode = subprocess.call(
                [python_path, script_path], creationflags=0x08000000, env=self.sys_env, shell=True)
            if rescode == 1:
                self.terminate = True
                self.server_error = True
                print("server error")
            elif rescode == 2:
                self.terminate = True
                self.server_error = True
                print("module jedi not found")
        except FileNotFoundError:
            print("python not found in PATH")

    def handle_socket(self, req_data):
        HOST = '127.0.0.1'  # The server's hostname or IP address
        PORT = 45362        # The port used by the server

        if not self.next:
            return
        self.next = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))
                s.sendall(req_data.encode())
                data = s.recv(65536)
                if not data:
                    return
                return data.decode()
        except ConnectionRefusedError:
            if self.terminate:
                return
            else:
                # print("server offline")
                thread = threading.Thread(target=self.run_server)
                thread.setDaemon(True)
                thread.start()
                if thread.is_alive():
                    return self.handle_socket(req_data)
                else:
                    return
        finally:
            self.next = True

    def complete(self, src):
        if src == "":
            return
        self.terminate = False
        return self.handle_socket(src)

    def exit(self):
        self.terminate = True
        self.handle_socket('exit_jedi')


def main():
    clt = Client()
    res = clt.complete("""import numpy as np
    	np.""")
    print(res)


if __name__ == '__main__':
    main()
