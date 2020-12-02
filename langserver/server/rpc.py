"""RPC encoder - decoder"""

import re

def encode(data: str) -> bytes:
	separator = b"\r\n\r\n"
	header = "Content-Length: %s"%(len(data))
	return header.encode("ascii")+separator+data.encode("utf-8")

class ContentInvalid(Exception):
	"""Unable resolve content"""
	pass

class ContentIncomplete(Exception):
	"""Content length less than defined length"""
	pass

class ContentOverflow(Exception):
	"""Content length greater than defined length"""
	pass

def _get_head_and_body(data: bytes) -> (str, str):
	dl = data.split(b"\r\n\r\n")
	if len(dl) != 2:
		raise ContentInvalid
	return (dl[0]).decode("ascii"), dl[1].decode("utf-8")

def _get_contentlength(header:str):
	cl = re.findall(r"Content-Length: (\d*)",header)
	if len(cl) != 1:
		raise ContentInvalid
	return int(cl[0])

def decode(data: bytes) -> str:
	head, body = _get_head_and_body(data)
	clen = _get_contentlength(head)
	if len(body) < clen:
		raise ContentIncomplete
	elif len(body) > clen:
		raise ContentOverflow
	else:
		return body