import rpc
import unittest
import logging

logging.basicConfig(level=logging.DEBUG)

class TestRPC(unittest.TestCase):
	def test_encode(self):
		tcase = [
			{
				"input":"hello world",
				"want":b'Content-Length: 11\r\n\r\nhello world'
			}
		]
		for tc in tcase:
			result = rpc.encode(tc["input"])
			self.assertEqual(result,tc["want"])

	def test_decode(self):
		tcase = [
			{
				"input":b"Content-Length: 11\r\n\r\nhello world",
				"exception":None,
				"want":"hello world"
			},
			{
				"input":b"Content-Length:\r\n\r\nhello world",
				"exception":rpc.ContentInvalid,
				"want":"hello world"
			},
			{
				"input":b"Content-Length: 11\r\n\r\nhello wo",
				"exception":rpc.ContentIncomplete,
				"want":"hello world"
			},
			{
				"input":b"Content-Length: 11\r\n\r\nhello worlds",
				"exception":rpc.ContentOverflow,
				"want":"hello world"
			}
		]
		for tc in tcase:
			if tc["exception"] is not None:
				self.assertRaises(tc["exception"],rpc.decode,tc["input"])
			else:
				result = rpc.decode(tc["input"])
				self.assertEqual(tc["want"],result)

	def test_parse_request(self):
		tcase = [
			{
				"input":'{"jsonrpc": "2.0", "id": "12", "method": "complete", "params": null}',
				"want":{"jsonrpc":"2.0","id":"12","method":"complete","params":None}
			}
		]
		for tc in tcase:
			rm = rpc.RequestMessage().parse(tc["input"])
			result = rm.message
			self.assertEqual(result,tc["want"])

	def test_request_message(self):
		tcase = [
			{
				"input":{"id":"12","method":"complete","params":None},
				"want":{"jsonrpc":"2.0","id":"12","method":"complete","params":None}
			}
		]
		for tc in tcase:
			rqm = rpc.RequestMessage()
			rqm.message=tc["input"]
			self.assertEqual(rqm.message, tc["want"])



	def test_response_error(self):		
		tcase = [
			{
				"input": dict(code="12",message="error message"),
				"want": {"code": "12", "message": "error message"}
			}
		]
		for tc in tcase:
			rerr = rpc.ResponseError(code=tc["input"]["code"],
				message=tc["input"]["message"],cocomsg="coco")
			result = rerr.error
			tc["want"].update({"cocomsg":"coco"})
			self.assertEqual(tc["want"],result)

	def test_response_package(self):
		rm = rpc.ResponseMessage()
		tcase = [
			{
				"input":rm.create(24,None,rpc.ResponseError(3,"some wrong").error),
				"want":{'jsonrpc': '2.0', 'id': 24,
					'results': None, 'error': {"code":3,"message":"some wrong"}}
			}
		]
		for tc in tcase:
			# logging.debug(rm.message)
			# logging.debug(tc["want"])
			result = rm.message
			self.assertEqual(tc["want"],result)


if __name__ == '__main__':
	unittest.main()