import socket
import rpc
import logging

class Server:
	def __init__(self):
		self.wait_next=True
		self.command = {}

	def run_command(self,command,*args):
		self.command[command](*args)

	def listen(self,buffer_size=1024):
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
						content = rpc.decode(data)
						break
					except rpc.ContentIncomplete:
						continue
					except rpc.ContentInvalid:
						break
					except rpc.ContentOverflow:
						break

				# result = self.process(content)
				conn.sendall(rpc.encode(content))	

	def run_server(self, buffer_size=1024):
		if self.wait_next:
			self.listen(buffer_size)


if __name__ == '__main__':
	s = Server()
	s.listen(24)