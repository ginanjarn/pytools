import socket, json
from .service.completion import Completion, jedi_error

def get_content_length(source:str) -> int:
    content_length = -1
    head_body = source.split("\r\n\r\n")
    if len(head_body) != 2:
        return
    head = head_body[0]
    head_row = head.split("\r\n")
    for row in head_row:
        key_val = row.split(": ")
        if len(key_val) != 2:
            break
        if key_val[0] == "Content-Length":
            content_length = key_val[1]
            break
    return int(content_length)

def get_content(source:str) -> str:
    head_body = source.split("\r\n\r\n")
    if len(head_body) != 2:
        return ''
    return head_body[1]

def get_body_length(source:str) -> int:
    head_body = source.split("\r\n\r\n")
    if len(head_body) != 2:
        return ''
    cnt_len = get_content_length(source)
    separator_len = len("\r\n\r\n")
    return len(head_body[0])+cnt_len+separator_len


class Server:
    def __init__(self):
        pass

    def run_service(self):        
        HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
        PORT = 65432        # Port to listen on (non-privileged ports are > 1023)
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            conn, addr = s.accept()
            with conn:
                print('Connected by', addr)
                body_len = 0
                body = b""
                while True:
                    data = conn.recv(1024)
                    if body_len==0:
                        get_body_length(data)
                    body += data
                    if len(body) >= body_len:
                        break

                result = self.do(get_content(body).decode())
                # TODO: Send result data
                conn.sendall(result.encode())
    def do(self,source):
        rpc_result = {"jsonrpc":"2.0"}
        rpc_error = {"code":0}
        try:
            # loaded from request
            obj = json.loads(source)
            method = obj["method"]
            params = obj["params"]
            rpc_result["id"] = obj["id"]

            result,err = self._act(method,params)
            rpc_result["results"]=result
            rpc_result["error"] = err


            content = json.dumps(result)
            msg = f"Content-Length: {len(content)}\r\n\r\n{content}"
            return msg
        except ValueError:
            # TODO return error response
            return {""}
   
    def _act(self, method, params):
        # ACTION---------------

        if method == "init":
            if jedi_error:
                rpc_result["results"]=None
                rpc_result["error"] = {"code":30,"message":"module jedi not found"}
                return rpc_result
            rpc_result["results"]=None
            return rpc_result


        if method == "textDocument/completion":
            # jedi use 1 based line
            line = params["line"]+1
            characters = params["characters"]
            source = "DocumentUri"
            c = Completion(source)
            results,err = c.complete(line,characters)
            if err:
                rpc_result["results"]=None
                rpc_result["error"]={"code":12,"message":err}
            else:
                rpc_result["results"] = results
            return rpc_result
            
        # UNKNOWN method -----------------
        else:
            # TODO return method not found
            return

        # TODO return success response
        # return



if __name__ == '__main__':
    s = Server()
    s.run_service()