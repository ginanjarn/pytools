"""Language-server param serializer"""


class Workspace:
    
    def __init__(self, path):
        self.path = path

    @staticmethod
    def serialize(path):
        params = {"path":path}
        return params

    @classmethod
    def deserialize(cls,params):
        cls.path = params["path"]
        return cls(path)


class Completion:

    def __init__(self, src, line, character):
        self.src = src
        self.line = line
        self.character = character

    @staticmethod
    def serialize(src, line, character):
        # Line position in a document (zero-based).
        params = {"textDocument": {"uri": src},
                  "position": {"line": line, "character": character}}
        return params

    @classmethod
    def deserialize(cls, params):
        src = params["textDocument"]["uri"]
        line = params["position"]["line"]
        # Jedi line position in a document (one-based).
        line += 1
        character = params["position"]["character"]
        return cls(src,line,character)


class Hover:

    def __init__(self, src, line, character):
        self.src = src
        self.line = line
        self.character = character

    @staticmethod
    def serialize(src, line, character):
        # Line position in a document (zero-based).
        params = {"textDocument": {"uri": src},
                  "position": {"line": line, "character": character}}
        return params

    @classmethod
    def deserialize(cls, params):
        src = params["textDocument"]["uri"]
        line = params["position"]["line"]
        # Jedi line position in a document (one-based).
        line += 1
        character = params["position"]["character"]
        return cls(src,line,character)