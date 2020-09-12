import unittest
import subprocess, os
import threading
import time
from service import pack, unpack, Client   # pylint: disable=import-error


def get_server():
    filepath = os.path.abspath(__file__)
    path_list = filepath.split(os.sep)
    serverpath = os.sep.join(path_list[:-2]+["server", "main.py"])
    return serverpath

def run_server(args):
    srv_return = subprocess.call(args, shell=True)
    if srv_return != 0:
        print("server error")

class ServiceTest(unittest.TestCase):

    # def test_pack(self):
    #     content = "hello world, packing"
    #     want = b"Content-Length: 20\r\n\r\nhello world, packing"
    #     expect = pack(content)
    #     self.assertEqual(want, expect, "packing")

    # def test_unpack(self):
    #     t1 = b"Content-Length: 27\r\n\r\nhello world, unpacking test"
    #     want = ("hello world, unpacking test", None)
    #     expect = unpack(t1)
    #     self.assertEqual(want, expect, "unpacking")

    # def test_client_connection(self):
    #     # subprocess.Popen(["python", get_server(), "--test_conn"])
    #     # wait server running
    #     time.sleep(3)
    #     c = Client(run_server=False)
    #     want = "hello world"
    #     expect = c.test_conn(want)
    #     c.exit()
    #     self.assertEqual(want, expect, "test connection")

    def test_exit_server(self):
        # c = Client(run_server=True)
        # time.sleep(3)
        # c.initialize()
        # c.exit()
        c = Client(run_server=False)
        # c.initialize()
        c.exit()

    # def test_client_completion(self):
    #     # subprocess.Popen(["python", get_server(), "--test"])
    #     # args = ["python", get_server(), "--test"]
    #     # thread = threading.Thread(target=run_server,args=(args,))
    #     # thread.setDaemon(True)
    #     # thread.start()
    #     # wait server running
    #     # time.sleep(3)
    #     c = Client(run_server=False)
    #     c.initialize()
    #     want = [{'label': 'sklearn', 'kind': 'module'}]
    #     expect = c.complete("from sk",0,7)
    #     c.exit()
    #     self.assertEqual(want, expect, "test completion")

    # def test_client_run_server(self):
    #     """this test will fail on first run because need time to run server"""
    #     # subprocess.Popen(["python", get_server(), "--test"])
    #     # wait server running
    #     time.sleep(3)
    #     c = Client(run_server=True)
    #     want = [{'label': 'sklearn', 'kind': 'module'}]
    #     expect = c.complete("from sk",0,7)
    #     c.exit()
    #     self.assertEqual(want, expect, "test run server")

    # def test_client_hover(self):
    #     # subprocess.Popen(["python", get_server(), "--test"])
    #     args = ["python", get_server(), "--test"]
    #     thread = threading.Thread(target=run_server,args=(args,))
    #     thread.setDaemon(True)
    #     thread.start()
    #     # wait server running
    #     time.sleep(3)
    #     c = Client(run_server=False)
    #     want = {'language': 'html', 'value': '<code>module : <a href="C:\\Users\\ginanjar\\miniconda3\\lib\\site-packages\\sklearn\\__init__.py:1:0">sklearn</a></code><h3>Machine learning module for Python</h3><p>==================================</p><p></p><p>sklearn is a Python module integrating classical machine</p><p>learning algorithms in the tightly-knit world of scientific Python</p><p>packages (numpy, scipy, matplotlib).</p><p></p><p>It aims to provide simple and efficient solutions to learning problems</p><p>that are accessible to everybody and reusable in various contexts:</p><p>machine-learning as a versatile tool for science and engineering.</p><p></p><p>See http://scikit-learn.org for complete documentation.</p>'}
    #     expect = c.hover("from sklearn.datasets import load_iris",0,9)
    #     c.exit()
    #     self.assertEqual(want, expect, "test hover")


if __name__ == '__main__':
    unittest.main()
