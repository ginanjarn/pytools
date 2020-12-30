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
        try:
            cparam = serializer.Hover.deserialize(params)
            self.src = cparam.src
            self.line = cparam.line
            self.character = cparam.character
        except serializer.DeserializeError:
            logger.exception("deserialize error", exc_info=True)
            raise serializer.DeserializeError from None

    def project(self, path):
        p = Project(path=path)
        return p

    def hover(self, src=None, line=None, character=None, project=None):
        if src is not None:
            self.src = src
        if line is not None:
            self.line = line
        if character is not None:
            self.character = character

        try:
            c = Script(source=self.src, project=project)
            result = c.help(self.line, self.character)

            logger.debug(self.src)
            logger.debug("line = %s, character = %s", self.line, self.character)
            if len(result) > 0:
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

            def docstring():
                if type_ in ["class", "function"]:
                    doc = data.docstring(raw=False)
                else:
                    doc = data.docstring(raw=True)

                doc = html.escape(doc, quote=False)
                return doc

            def split_p(src):
                return src.split("\n\n")

            def wrap_p(line):
                return "<p>%s</p>" % (line)

            def split_br(src):
                return src.split("\n")

            def join_br(lines):
                if not isinstance(lines, list):
                    raise TypeError
                return "<br>".join(lines)

            if type_ == "keyword":
                logger.debug("this is keyword")
                yield get_header()
            else:
                yield get_header()
                doc = docstring()
                if doc != "":
                    paragraphs = split_p(doc)
                    for par in paragraphs:
                        lines = split_br(par)
                        par_body = join_br(lines)
                        yield wrap_p(par_body)

        except Exception:
            logger.exception("some wrong", exc_info=True)
            raise HoverError from None
