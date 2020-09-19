import unittest
from main import pack, unpack, Server   # pylint: disable=no-name-in-module


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

    def test_server_complete(self):
        want = [{'label': 'sklearn', 'kind': 'module'}]
        s = Server()
        params = {"textDocument":{"uri":"from sk"},"position":{"line":0,"character":7}}
        result, _ = s.complete(params)
        expect = result
        self.assertEqual(want, expect, "complete")

    def test_server_hover(self):
        want = {'contents': {'language': 'html', 'value': '<code>module : <a href="C:\\Users\\ginanjar\\miniconda3\\lib\\site-packages\\sklearn\\__init__.py:1:0">sklearn</a></code><h3>Machine learning module for Python</h3><p>==================================</p><p></p><p>sklearn is a Python module integrating classical machine</p><p>learning algorithms in the tightly-knit world of scientific Python</p><p>packages (numpy, scipy, matplotlib).</p><p></p><p>It aims to provide simple and efficient solutions to learning problems</p><p>that are accessible to everybody and reusable in various contexts:</p><p>machine-learning as a versatile tool for science and engineering.</p><p></p><p>See http://scikit-learn.org for complete documentation.</p>'}}
        want1 = {'contents': {'language': 'html', 'value': '<code>keyword : from</>'}}
        s = Server()
        params = {"textDocument":{"uri":"from sklearn.datasets import load_iris"},"position":{"line":0,"character":9}}
        params1 = {"textDocument":{"uri":"from sklearn.datasets import load_iris"},"position":{"line":0,"character":3}}
        result, _ = s.hover(params)
        result1, _ = s.hover(params1)
        self.assertEqual(want,result,"non keyword case")
        self.assertEqual(want1,result1,"keyword case")
        pass


if __name__ == '__main__':
    unittest.main()
