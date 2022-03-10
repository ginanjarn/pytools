"""handle services associated to jedi module"""

import logging
import os

from html import escape
from typing import List, Dict, Any

from jedi import Script, Project
from jedi.api.classes import Completion as JediCompletion
from jedi.api.classes import Name as JediName

LOGGER = logging.getLogger(__name__)
# LOGGER.setLevel(logging.DEBUG)
STREAM_HANDLER = logging.StreamHandler()
LOG_TEMPLATE = "%(levelname)s %(asctime)s %(filename)s:%(lineno)s  %(message)s"
STREAM_HANDLER.setFormatter(logging.Formatter(LOG_TEMPLATE))
LOGGER.addHandler(STREAM_HANDLER)


class Service:
    def __init__(self, *, project_path=None):

        self.project = (
            Project(project_path)
            if project_path and os.path.exists(project_path)
            else None
        )
        self._source = ""
        self.script = None

    def change_workspace(self, project_path):
        self.project = (
            Project(project_path)
            if project_path and os.path.exists(project_path)
            else None
        )
        self._source = ""
        self.script = None

    def complete(self, source, row, col) -> List[JediCompletion]:
        if not self._source.startswith(source):
            self._source = source
            self.script = Script(self._source, project=self.project)

        return self.script.complete(row, col)

    def hover(self, source, row, col) -> List[JediName]:
        if not self._source.startswith(source):
            self._source = source
            self.script = Script(self._source, project=self.project)

        return self.script.help(row, col)


def completion_to_rpc(completions: List[JediCompletion]) -> Dict[str, Any]:
    """build completion rpc"""

    def build_completion(completion: JediCompletion):
        try:
            completion_type = completion.type
            annotation = (
                completion._get_docstring_signature()
                if completion_type in {"class", "function"}
                else ""
            )
            return {
                "label": completion.name,
                "annotation": annotation,
                "type": completion_type,
            }
        except Exception as err:
            LOGGER.debug("parsing completion error: %s", repr(err))
            return None

    results = [build_completion(item) for item in completions]
    LOGGER.debug("results: %s", results)
    return [result for result in results if result]


def escape_characters(s: str):
    """escape html character"""
    return escape(s, quote=False).replace("\n", "<br>").replace("  ", "&nbsp;&nbsp;")


def documentation_to_rpc(names: List[JediName]) -> Dict[str, Any]:
    """build documentation rpc"""

    def build_documentation(name: JediName) -> str:
        LOGGER.debug(f"name: {repr(name)}")
        try:
            module_name = name.module_name
            module_path = name.module_path
            type_ = name.type
            signature = (
                name._get_docstring_signature()
                if type_ in {"class", "function"}
                else ""
            )
            docstring = name._get_docstring()
        except Exception as err:
            LOGGER.debug(err)
            return ""

        # header
        header = (
            f"module: <code>{module_name}</code>"
            if module_name and module_name != "__main__"
            else ""
        )
        # title
        title = f"<h3>{type_} <strong><code>{name.name}</code></strong></h3>"
        # signature
        signature = (
            f"<p><code>{escape_characters(signature)}</code></p>" if signature else ""
        )
        # body
        body = f"<p>{escape_characters(docstring)}</p>" if docstring else ""

        # footer
        footer = ""
        try:
            row, col = name.line, name.column
            # use one-based column index
            col += 1
            module_path = (
                module_path if module_path and module_path != "__main__" else ""
            )
            footer = f"<a href='{module_path}:{row}:{col}'>Go to definition</a>"
        except Exception as err:
            LOGGER.debug(err)
            return ""
        else:
            result = "\n".join(
                [item for item in (header, title, signature, body, footer) if item]
            )
            return f"<div>{result}</div>"

    result = {"content": build_documentation(names[0])}
    LOGGER.debug("result: %s", result)
    return result
