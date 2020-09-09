import unittest
from main import pack, unpack   # pylint: disable=no-name-in-module


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


if __name__ == '__main__':
    unittest.main()
