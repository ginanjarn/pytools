import unittest
import subprocess, os
import time
from service import pack, unpack, Client   # pylint: disable=import-error


def get_server():
    filepath = os.path.abspath(__file__)
    path_list = filepath.split(os.sep)
    serverpath = os.sep.join(path_list[:-2]+["server", "main.py"])
    return serverpath


class ServiceTest(unittest.TestCase):

    def test_pack(self):
        content = "hello world, packing"
        want = b"Content-Length: 20\r\n\r\nhello world, packing"
        expect = pack(content)
        self.assertEqual(want, expect, "packing")

    def test_unpack(self):
        t1 = b"Content-Length: 27\r\n\r\nhello world, unpacking test"
        want = ("hello world, unpacking test", None)
        expect = unpack(t1)
        self.assertEqual(want, expect, "unpacking")

    def test_client_connection(self):
        # subprocess.Popen(["python", get_server(), "--test_conn"])
        # wait server running
        time.sleep(3)
        c = Client(run_server=False)
        want = "hello world"
        expect = c.test_conn(want)
        self.assertEqual(want, expect, "test connection")

    def test_client_completion(self):
        # subprocess.Popen(["python", get_server(), "--test"])
        # wait server running
        time.sleep(3)
        c = Client(run_server=False)
        want = [{'label': 'sklearn', 'kind': 'module'}]
        expect = c.complete("from sk",0,7)
        self.assertEqual(want, expect, "test connection")

    # def test_client_run_server(self):
    #     """this test will fail on first run because need time to run server"""
    #     # subprocess.Popen(["python", get_server(), "--test"])
    #     # wait server running
    #     time.sleep(3)
    #     c = Client(run_server=True)
    #     want = [{'label': 'sklearn', 'kind': 'module'}]
    #     expect = c.complete("from sk",0,7)
    #     self.assertEqual(want, expect, "test run server")


if __name__ == '__main__':
    unittest.main()
