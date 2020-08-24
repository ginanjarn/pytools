import socket
from jedi import Script
import sys


class Jedi:
    def __init__(self, source):
        self.source = source

    def get_pos(self):
        """get line and col from source"""
        if self.source == "":
            return
        lines = self.source.split("\n")
        line_pos = len(lines)
        col_pos = len(lines[-1])
        return line_pos, col_pos

    def get_completions(self):
        """get completion"""
        """return completion and completion type"""
        if self.source == "":
            return
        s = Script(self.source)
        line, col = self.get_pos()
        cmp_list = s.complete(line, col)
        if len(cmp_list) == 0:
            return

        completions = []

        for cmp in cmp_list:
            name = cmp.name_with_symbols
            ctype = cmp.type
            completions.append(",,".join([name, ctype]))
        return "\n".join(completions)


def complete(src):
    if src == "":
        return
    jedi = Jedi(src)
    return jedi.get_completions()


def handle_socket():
    HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
    PORT = 45362        # Port to listen on (non-privileged ports are > 1023)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        terminate = False
        while True:
            conn, addr = s.accept()
            with conn:
                print('Connected by', addr)
                while True:
                    data = conn.recv(65536)
                    if not data:
                        break
                    data_decoded = data.decode()
                    if data_decoded == "exit_jedi":
                        terminate = True
                    else:
                        # print(data_decoded)
                        result = complete(data_decoded)
                        # print(result)

                        data = result.encode() if result != None else "None".encode()

                    conn.sendall(data)

                if terminate:
                    break


def main():
    handle_socket()


if __name__ == '__main__':
    main()
