"""Language-server param serializer"""

from typing import Dict, Any


class DeserializeError(Exception):
    """Unable to deserialize content"""

    ...


class WorkspaceParams:
    def __init__(self, path: str) -> None:
        self.path = path

    @staticmethod
    def serialize(path: str) -> Dict[str, Any]:
        params = {"path": path}
        return params

    @classmethod
    def deserialize(cls, params: Dict[str, Any]) -> "WorkspaceParams":
        try:
            path = params["path"]
        except Exception:
            raise DeserializeError from None
        return cls(path)


class CompletionParams:
    def __init__(self, src: str, line: int, character: int) -> None:
        self.src = src
        self.line = line
        self.character = character

    @staticmethod
    def serialize(src: str, line: int, character: int) -> Dict[str, Any]:
        # Line position in a document (zero-based).
        params = {
            "textDocument": {"uri": src},
            "position": {"line": line, "character": character},
        }
        return params

    @classmethod
    def deserialize(cls, params: Dict[str, Any]) -> "CompletionParams":
        try:
            src = params["textDocument"]["uri"]
            line = params["position"]["line"]
            # Jedi line position in a document (one-based).
            line += 1
            character = params["position"]["character"]
        except Exception:
            raise DeserializeError from None
        return cls(src, line, character)


class HoverParams:
    def __init__(self, src: str, line: int, character: int) -> None:
        self.src = src
        self.line = line
        self.character = character

    @staticmethod
    def serialize(src: str, line: int, character: int) -> Dict[str, Any]:
        # Line position in a document (zero-based).
        params = {
            "textDocument": {"uri": src},
            "position": {"line": line, "character": character},
        }
        return params

    @classmethod
    def deserialize(cls, params: Dict[str, Any]) -> "HoverParams":
        try:
            src = params["textDocument"]["uri"]
            line = params["position"]["line"]
            # Jedi line position in a document (one-based).
            line += 1
            character = params["position"]["character"]
        except Exception:
            raise DeserializeError from None
        return cls(src, line, character)


class FormattingParams:
    def __init__(self, src: str) -> None:
        self.src = src

    @staticmethod
    def serialize(src: str) -> Dict[str, Any]:
        params = {"textDocument": {"uri": src}}
        return params

    @classmethod
    def deserialize(cls, params: Dict[str, Any]) -> "FormattingParams":
        try:
            src = params["textDocument"]["uri"]
        except Exception:
            raise DeserializeError from None
        return cls(src)
