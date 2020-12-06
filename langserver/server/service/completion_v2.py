"""Completion module"""


COMPLETION_CAPABLE = True


try:
    from jedi import Script, Project
    from . import serializer
except ModuleNotFoundError:
    COMPLETION_CAPABLE = False


def capability():
    return {"completionProvider": {"resolveProvider": COMPLETION_CAPABLE}}


class Completion:
    def __init__(self, params):
        cparam = serializer.Completion.deserialize(params)
        self.src = cparam.src
        self.line = cparam.line
        self.character = cparam.character

    def project(self, path):
        p = Project(path=path)
        return p

    def complete(self, src=None, line=None, character=None, project=None):
        if src is not None:
            self.src = src
        if line is not None:
            self.line = line
        if character is not None:
            self.character

        c = Script(source=self.src, project=project)
        result = c.complete(self.line, self.character)
        completion_list = []
        for r in result:
            completion = {}
            completion["label"] = r.name_with_symbols
            completion["kind"] = r.type
            completion_list.append(completion)
        return completion_list
