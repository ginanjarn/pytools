import unittest
import serializer as sr

class Completion(unittest.TestCase):
	def test_serializer(self):
		tcase = [
			{
				"test":sr.Completion.serialize("hello world",1,11),
				"want":{"textDocument":{"uri": "hello world"},
					"position":{"line": 1,"character": 11}}
			}
		]
		for tc in tcase:
			self.assertEqual(tc["test"],tc["want"])

	def test_deserealizer(self):
		tcase = [
			{
				"test":{"textDocument":{"uri": "hello world"},
					"position":{"line": 0,"character": 11}},
				"want":{"src":"hello world","line":1,"character":11}
			}
		]
		for tc in tcase:
			res = sr.Completion.deserialize(tc["test"])
			self.assertEqual(tc["want"],{"src":res.src,"line":res.line,"character":res.character})

if __name__ == '__main__':
	unittest.main()