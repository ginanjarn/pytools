import socket,json

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

class Client:
	def __init__(self,python=None,env=None):
		self.python = python
		self.env = env
		self._server_running = False
		self._server_error = False
		self.req_id = 0

	def _run_server(self):
		run_server_cmd = ["python", "-"]

        if os.name == "nt":
            # linux subprocess module does not have STARTUPINFO
            # so only use it if on Windows
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(run_server_cmd,shell=True, env=self.env, startupinfo=si)
        else:
            subprocess.Popen(run_server_cmd,shell=True, env=self.env)

		pass

	def request(self,method,params):
		try:
			HOST = '127.0.0.1'  # The server's hostname or IP address
			PORT = 65432        # The port used by the server
			
			with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
			    s.connect((HOST, PORT))
			    self.req_id +=1
			    # params = json.dumps(params)
			    rpc_request = {"jsonrpc":"2.0","id":f"{self.req_id}",'method':method,"params":params}
			    content = json.dumps(rpc_request)
			    msg = f"Content-Length: {len(content)}\r\n\r\n{content}"
			    s.sendall(msg)

			    resp_len = 0
			    resp_body = b""
			    while True:
				    data = s.recv(1024)
				    if resp_len == 0:
					    resp_len = get_body_length(data)
				    resp_body += data
				    if resp_len >= len(resp_body):
				    	break
		    	resp_content = get_content(resp_body)
		    	resp_obj = json.loads(resp_content)
			
			print('Received', repr(data))
		except ConnectionRefusedError:
			# run server if not running