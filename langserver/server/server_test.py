import socket
import rpc

HOST = "127.0.0.1"
PORT = 1205


def send_message(data: bytes) -> bytes:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(data)
        data = s.recv(1024)
    return data


def request(msg):
    emsg = rpc.encode(msg)
    result = send_message(emsg)
    return rpc.decode(result)


def exit():
    # msg = rpc.RequestMessage().create(12,"exit")
    msg = rpc.RequestMessage()
    msg.create(12, "exit")
    print(str(msg))
    result = request(str(msg))
    print(result)


def ping(data=None):
    msg = rpc.RequestMessage()
    msg.create(12, "ping", data)
    print(str(msg))
    result = request(str(msg))
    print(result)