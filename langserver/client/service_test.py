import unittest
import os
from service import get_content_length, get_content, get_body_length


class ServiceTest(unittest.TestCase):

    def test_content_length(self):
        raw = "Content-Length: 24\r\nContent-Type: charset;utf-8\r\n\r\nhello world. how are you"
        want = 24
        self.assertEqual(get_content_length(raw), want, "content length equal")

    def test_get_content(self):
        raw = "Content-Length: 24\r\nContent-Type=charset;utf-8\r\n\r\nhello world. how are you"
        want = "hello world. how are you"
        self.assertEqual(get_content(raw), want, "content equal")

    def test_get_body_len(self):
        raw = "Content-Length: 24\r\nContent-Type=charset;utf-8\r\n\r\nhello world. how are you"
        want = len(raw)
        self.assertEqual(get_body_length(raw), want, "body length equal")

    def test_server_valid(self):
        def get_server():
            filepath = os.path.abspath(__file__)
            path_list = filepath.split(os.sep)
            serverpath = os.sep.join(path_list[:-2]+["server","service.py"])
            return serverpath
        want = True
        expect = os.path.isfile(get_server())
        self.assertEqual(want,expect,"path valid")

if __name__ == '__main__':
    unittest.main()
