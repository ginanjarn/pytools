import socket
import rpc
import re
import service.serializer as serializer

HOST = "127.0.0.1"
PORT = 1205


def send_message(data: bytes, buffer_size=1024) -> bytes:
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


def request(msg):
    emsg = rpc.encode(msg)
    result = send_message(emsg)
    return rpc.decode(result)


def exit():
    msg = rpc.RequestMessage().create(12, "exit")
    print(str(msg))
    result = request(str(msg))
    print(result)


def initialize():
    msg = rpc.RequestMessage().create(12, "initialize")
    print(str(msg))
    result = request(str(msg))
    print(result)


def ping(data=None):
    msg = rpc.RequestMessage().create(12, "ping", data)
    print(str(msg))
    result = request(str(msg))
    print(result)


def complete(data=None):
    if data is None:
        data = "import os\nos.pat"
    src = data
    strspl = data.split("\n")
    ln_idx = len(strspl)
    ln_idx -= 1  # langserver specification use zero-based index
    chr_idx = len(strspl[-1])
    params = serializer.Completion.serialize(src, ln_idx, chr_idx)
    msg = rpc.RequestMessage().create(25, "textDocument/completion", params)
    print(str(msg))
    result = request(str(msg))
    print(result)

def hover(data=None):
    if data is None:
        data = "import os\nos.path"
    src = data
    strspl = data.split("\n")
    ln_idx = len(strspl)
    ln_idx -= 1  # langserver specification use zero-based index
    last_word = re.findall(r"\w+",data)[-1]
    chr_idx = len(strspl[-1])-len(last_word)
    params = serializer.Completion.serialize(src, ln_idx, chr_idx)
    msg = rpc.RequestMessage().create(25, "textDocument/hover", params)
    print(str(msg))
    result = request(str(msg))
    print(result)

def set_workspace_config(path="this_path"):
    params = serializer.Workspace.serialize(path=path)
    msg = rpc.RequestMessage().create(40,"workspace/didChangeConfiguration",params)
    print(str(msg))
    result = request(str(msg))
    print(result)

def formatting(data=None):
    src = """import os,time
name=os.getcwd()


import re
ca = re.findall(r"[a-z]*","hello")"""
    
    params = serializer.Formatting.serialize(src)
    msg = rpc.RequestMessage().create(25, "textDocument/formatting", params)
    print(str(msg))
    result = request(str(msg))
    print(result)
