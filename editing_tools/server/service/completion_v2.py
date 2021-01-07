"""Completion module"""


import logging
from typing import Iterator, Dict, Any


logger = logging.getLogger("formatting")
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


COMPLETION_CAPABLE = True


try:
    from jedi import Script, Project  # type: ignore
except ModuleNotFoundError:
    COMPLETION_CAPABLE = False


def capability() -> Dict[str, Any]:
    return {"completionProvider": {"resolveProvider": COMPLETION_CAPABLE}}


class CompletionError(Exception):
    """Completion Error"""

    ...


class Completion:
    def __init__(self, src: str, line: int, character: int) -> None:
        self.src = src
        self.line = line
        self.character = character

    @staticmethod
    def project(path: str) -> "Project":
        proj = Project(path=path)
        return proj

    def complete(self, project: "Project" = None) -> Iterator[Dict[str, Any]]:
        """Fetch completion

        Yield:
            completion(str): completion result
        """

        try:
            script = Script(source=self.src, project=project)
            results = script.complete(self.line, self.character)
            for result in results:
                yield {"label": result.name_with_symbols, "kind": result.type}
        except Exception:
            logger.exception("fetch completion error", exc_info=True)
            raise CompletionError from None
