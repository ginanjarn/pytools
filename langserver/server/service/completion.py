jedi_error = None
try:
	from jedi import Script
except ModuleNotFoundError:
	module_error = "jedi"

class Completion:
	def __init__(self,source):
		self.source = source
	def complete(self,line:int,character:int) -> (any,any):
		try:
			c = Script(source=self.source)
			result = c.complete(line,character)
			completion_list = []
			for r in result:
				completion = {}
				completion["label"] = r.name_with_symbols
				completion["kind"] = r.type
				completion_list.append(completion)
			return completion_list,None
		except ValueError as e:
			return None, str(e)
