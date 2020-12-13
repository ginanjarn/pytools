import re
import unittest

def conda_dir(name):
	found = re.findall(r"\w+conda\w*",name)
	conda = found[0] if len(found) > 0 else None
	return conda

def build_setting(manager, name, env_path, python_exc="python"):
	return {"manager":manager, "name": name, "path": env_path, "python_exc": python_exc}

class TestCondaTools(unittest.TestCase):
	def test_condadir(self):
		tcase = {
					"test": ["conda","anaconda","miniconda","anaconda2","anaconda3","miniconda2","miniconda3"],
					"want": [None,"anaconda","miniconda","anaconda2","anaconda3","miniconda2","miniconda3"]
				}
		idx = 0
		for t in tcase["test"]:
			res = conda_dir(t)
			self.assertEqual(res, tcase["want"][idx])
			idx += 1


if __name__ == '__main__':
	unittest.main()