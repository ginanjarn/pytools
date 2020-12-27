"""Completion module"""
import logging


logger = logging.getLogger("formatting")
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


COMPLETION_CAPABLE = True


try:
    from jedi import Script, Project
    from . import serializer
except ModuleNotFoundError:
    COMPLETION_CAPABLE = False


def capability():
    return {"completionProvider": {"resolveProvider": COMPLETION_CAPABLE}}


class CompletionError(Exception):
    """Completion Error"""

    ...


class Completion:
    def __init__(self, params):
        try:
            cparam = serializer.Completion.deserialize(params)
            self.src = cparam.src
            self.line = cparam.line
            self.character = cparam.character
        except serializer.DeserializeError:
            logger.exception("deserialize error", exc_info=True)
            raise serializer.DeserializeError from None

    def project(self, path):
        p = Project(path=path)
        return p

    def complete(self, src=None, line=None, character=None, project=None):
        if src is not None:
            self.src = src
        if line is not None:
            self.line = line
        if character is not None:
            self.character = character

        try:
            c = Script(source=self.src, project=project)
            result = c.complete(self.line, self.character)
            for r in result:
                completion = {}
                completion["label"] = r.name_with_symbols
                completion["kind"] = r.type
                yield completion
        except Exception:
            logger.exception("fetch completion error", exc_info=True)
            raise CompletionError from None
