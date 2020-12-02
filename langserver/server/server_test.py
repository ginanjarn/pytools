import socket
import unittest
from server import Server

HOST = "127.0.0.1"
PORT = 1205

def send_message(data):
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
	    s.connect((HOST, PORT))
	    s.sendall(data)
	    data = s.recv(1024)	
	return data



if __name__ == '__main__':
	unittest.main()