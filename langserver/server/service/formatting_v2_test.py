import logging
import unittest
import re


logger = logging.getLogger("formatting_test")
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter(
    '%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


class TestFormatting(unittest.TestCase):
    def test_scope_sign(self):
        tcase = [
            {
                "test": "@@ -1,5 @@",
                "want": (1, 5)
            },
            {
                "test": "@@ -2,6 +2,10 @@",
                "want": (2, 6, 2, 10)
            }
        ]

        def parse_diff_header(param):
            result = None
            # @@ -a,b +c,d @@
            rst = re.findall(r"@@\s\-(\d*),(\d*)\s\+(\d*),(\d*)\s@@", param)
            logger.debug(rst)
            if len(rst) == 1:
                result = rst[0]
                result = int(result[0]), int(result[1]), int(
                    result[2]), int(result[3])
            else:
                rst = re.findall(r"@@\s\-(\d*),(\d*)\s@@", param)
                logger.debug(rst)
                if len(rst) == 1:
                    result = rst[0]
                    result = int(result[0]), int(result[1])
            if result is None:
                raise ValueError
            return result
        for tc in tcase:
            result = parse_diff_header(tc["test"])
            self.assertEqual(result, tc["want"])


if __name__ == '__main__':
    unittest.main()