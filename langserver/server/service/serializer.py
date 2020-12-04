"""Language-server param serializer"""


class Workspace:
	path = ""

	@staticmethod
	def serialize(path):
		params = {"path":path}
		return params

	@classmethod
	def deserialize(cls,params):
		cls.path = params["path"]
		return cls


class Completion:
    src = None
    line = None
    character = None

    @staticmethod
    def serialize(src, line, character):
        # Line position in a document (zero-based).
        params = {"textDocument": {"uri": src},
                  "position": {"line": line, "character": character}}
        return params

    @classmethod
    def deserialize(cls, params):
        cls.src = params["textDocument"]["uri"]
        cls.line = params["position"]["line"]
        # Jedi line position in a document (one-based).
        cls.line += 1
        cls.character = params["position"]["character"]
        return cls