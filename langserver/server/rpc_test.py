import rpc
import unittest

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

if __name__ == '__main__':
	unittest.main()