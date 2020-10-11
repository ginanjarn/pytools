import re

def conda_dir(name):
	conda = None
	found = re.findall(r"\w+conda\w*",name)
	if len(found) > 0:
		conda = found[0]
	return conda

if __name__ == '__main__':
	tc = ["conda","anaconda","miniconda","anaconda2","anaconda3","miniconda2","miniconda3"]
	rs = [None,"anaconda","miniconda","anaconda2","anaconda3","miniconda2","miniconda3"]
	i=0
	for c in tc:
		result = conda_dir(c)
		print(result==rs[i])
		i+=1