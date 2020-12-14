"""Language-server param serializer"""


class DeserializeError(Exception):
    """Unable to deserialize content"""
    pass


class Workspace:

    def __init__(self, path):
        self.path = path

    @staticmethod
    def serialize(path):
        params = {"path": path}
        return params

    @classmethod
    def deserialize(cls, params):
        try:
            path = params["path"]
        except Exception:
            raise DeserializeError
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
        try:
            src = params["textDocument"]["uri"]
            line = params["position"]["line"]
            # Jedi line position in a document (one-based).
            line += 1
            character = params["position"]["character"]
        except Exception:
            raise DeserializeError
        return cls(src, line, character)


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
        try:
            src = params["textDocument"]["uri"]
            line = params["position"]["line"]
            # Jedi line position in a document (one-based).
            line += 1
            character = params["position"]["character"]
        except Exception:
            raise DeserializeError
        return cls(src, line, character)


class Formatting:

    def __init__(self, src):
        self.src = src

    @staticmethod
    def serialize(src):
        params = {"textDocument": {"uri": src}}
        return params

    @classmethod
    def deserialize(cls, params):
        try:
            src = params["textDocument"]["uri"]
        except Exception:
            raise DeserializeError
        return cls(src)