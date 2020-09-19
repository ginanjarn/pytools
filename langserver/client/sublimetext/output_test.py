import unittest
import completion

class TestSublimeOutput(unittest.TestCase):
    def test_completion(self):
        data = [{"label":"sklearn","kind":"module"},{"label":"skimage","kind":"module"}]
        want = [("sklearn\tmodule","sklearn"),("skimage\tmodule","skimage")]
        expect = completion.format_code(data)
        self.assertEqual(want,expect,"completion format valid")
        # pass

if __name__ == "__main__":
    unittest.main()