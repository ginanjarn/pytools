"""Hover help module"""

import logging
import html


logger = logging.getLogger("hover")
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


HOVER_CAPABLE = True


try:
    from jedi import Script, Project
    from . import serializer
except ModuleNotFoundError:
    HOVER_CAPABLE = False


def capability():
    return {"hoverProvider": HOVER_CAPABLE}


class HoverError(Exception):
    """Hover Error"""

    ...


class Hover:
    def __init__(self, params):
        cparam = serializer.Hover.deserialize(params)
        self.src = cparam.src
        self.line = cparam.line
        self.character = cparam.character

    @staticmethod
    def project(path):
        proj = Project(path=path)
        return proj

    def hover(self, project=None):
        """Get documentation

        Return:
            documentation object"""
        try:
            script = Script(source=self.src, project=project)
            result = script.help(self.line, self.character)

            logger.debug(self.src)
            logger.debug("line = %s, character = %s", self.line, self.character)

            if result:  # for list
                prebuit_doc = self.build_doc(result[0])
                prebuit_doc = "".join(prebuit_doc)
            else:
                prebuit_doc = ""
        except Exception:
            raise HoverError from None

        return {"contents": {"language": "html", "value": prebuit_doc}}

    def build_doc(self, data):
        try:
            type_ = data.type
            name = data.name

            logger.debug("doc type= %s, name= %s", type_, name)

            def get_header():
                if type_ == "keyword":
                    header = "%s %s" % (type_, name)
                else:
                    module_path = data.module_path
                    module_path = module_path if module_path is not None else ""
                    line = data.line
                    column = (data.column + 1) if data.column is not None else None

                    href = "%s:%s:%s" % (module_path, line, column)
                    header = '%s <a href="%s">%s</a>' % (type_, href, name)
                    logger.debug(header)
                return header

            def get_docstring():
                if type_ in ["class", "function"]:
                    doc = data.docstring(raw=False)
                else:
                    doc = data.docstring(raw=True)

                doc = html.escape(doc, quote=False)
                return doc

            def wrap_paragraph(line):
                return "<p>%s</p>" % (line)

            def wrap_line_break(content):
                lines = content.split("\n")
                return "<br>".join(lines)

            if type_ == "keyword":
                logger.debug("this is keyword")
                yield get_header()
            else:
                yield get_header()
                doc = get_docstring()
                if doc:  # for string
                    paragraphs = doc.split("\n\n")
                    for paragraph in paragraphs:
                        body = wrap_line_break(paragraph)
                        yield wrap_paragraph(body)

        except Exception:
            logger.exception("some wrong", exc_info=True)
            raise HoverError from None
