import unittest
import serializer as sr


class Completion(unittest.TestCase):
    def test_serializer(self):
        tcase = [
            {
                "test": sr.Completion.serialize("hello world", 1, 11),
                "want": {"textDocument": {"uri": "hello world"},
                         "position": {"line": 1, "character": 11}}
            }
        ]
        for tc in tcase:
            self.assertEqual(tc["test"], tc["want"])

    def test_deserializer(self):
        tcase = [
            {
                "test": {"textDocument": {"uri": "hello world"},
                         "position": {"line": 0, "character": 11}},
                "want": {"src": "hello world", "line": 1, "character": 11}
            }
        ]
        for tc in tcase:
            res = sr.Completion.deserialize(tc["test"])
            self.assertEqual(
                tc["want"], {"src": res.src, "line": res.line, "character": res.character})

        tcase = [
            {
                "test": {"textDocument": {},
                         "position": {"line": 0, "character": 11}},
            }
        ]
        for tc in tcase:
            self.assertRaises(sr.DeserializeError,
                              sr.Completion.deserialize, tc["test"])


class Hover(unittest.TestCase):
    def test_serializer(self):
        tcase = [
            {
                "test": sr.Hover.serialize("hello world", 1, 11),
                "want": {"textDocument": {"uri": "hello world"},
                         "position": {"line": 1, "character": 11}}
            }
        ]
        for tc in tcase:
            self.assertEqual(tc["test"], tc["want"])

    def test_deserializer(self):
        tcase = [
            {
                "test": {"textDocument": {"uri": "hello world"},
                         "position": {"line": 0, "character": 11}},
                "want": {"src": "hello world", "line": 1, "character": 11}
            }
        ]
        for tc in tcase:
            res = sr.Hover.deserialize(tc["test"])
            self.assertEqual(
                tc["want"], {"src": res.src, "line": res.line, "character": res.character})

        tcase = [
            {
                "test": {"textDocument": {},
                         "position": {"line": 0, "character": 11}},
            }
        ]
        for tc in tcase:
            self.assertRaises(sr.DeserializeError,
                              sr.Completion.deserialize, tc["test"])


class Formatting(unittest.TestCase):
    def serialize(self):
        tcase = [
            {
                "test": sr.Formatting.serialize("hello world"),
                "want": {"textDocument": {"uri": "hello world"}}
            }
        ]
        for tc in tcase:
            self.assertEqual(tc["test"], tc["want"])

    def deserialize(self):
        tcase = [
            {
                "test": {"textDocument": {"uri": "hello world"}},
                "want": {"src": "hello world"}
            }
        ]
        for tc in tcase:
            res = sr.Hover.deserialize(tc["test"])
            self.assertEqual(tc["want"], {"src": res.src})

        tcase = [
            {
                "test": {"textDocument": {}, },
            }
        ]
        for tc in tcase:
            self.assertRaises(sr.DeserializeError,
                              sr.Completion.deserialize, tc["test"])


class Workspace(unittest.TestCase):
    def serialize(self):
        tcase = [
            {
                "test": sr.Workspace.serialize(path="hello/path"),
                "want": {"path": "hello/path"}
            }
        ]
        for tc in tcase:
            self.assertEqual(tc["test"], tc["want"])

    def deserialize(self):
        tcase = [
            {
                "test": {"path": "hello/path"},
                "want": {"path": "hello/path"}
            }
        ]
        for tc in tcase:
            res = sr.Workspace.deserialize(tc["test"])
            self.assertEqual(tc["want"], {"path": res.path})

        tcase = [
            {
                "test": {"textDocument": {}, },
            }
        ]
        for tc in tcase:
            self.assertRaises(sr.DeserializeError,
                              sr.Workspace.deserialize, tc["test"])


if __name__ == '__main__':
    unittest.main()