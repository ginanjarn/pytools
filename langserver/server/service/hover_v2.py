"""Hover help module"""

import logging


logger = logging.getLogger("hover")
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter(
    '%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
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
    pass


class Hover:
    def __init__(self, params):
        try:
            cparam = serializer.Hover.deserialize(params)
            self.src = cparam.src
            self.line = cparam.line
            self.character = cparam.character
        except serializer.DeserializeError:
            raise serializer.DeserializeError

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
            logger.debug("line = %s, character = %s",
                         self.line, self.character)
            prebuit_doc = self.build_doc(result[0]) if len(result) > 0 else ""
            ret = {"contents": {"language": "html", "value": prebuit_doc}}
        except Exception:
            raise HoverError

        return ret

    def build_doc(self, data):
        result = None
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
                    column = (data.column +
                              1) if data.column is not None else None

                    href = "%s:%s:%s" % (module_path, line, column)
                    header = "%s <a href=%s>%s</a>" % (type_, href, name)
                    logger.debug(header)
                return header

            def docstring():
                if type_ in ["class", "function"]:
                    doc = data.docstring(raw=False)
                else:
                    doc = data.docstring(raw=True)
                return doc

            def split_p(src):
                return src.split("\n\n")

            def wrap_p(lines):
                if not isinstance(lines, list):
                    raise TypeError
                return ["<p>%s</p>" % (line) for line in lines]

            def split_br(src):
                return src.split("\n")

            def join_br(lines):
                if not isinstance(lines, list):
                    raise TypeError
                return "<br>".join(lines)

            def join(lines):
                if not isinstance(lines, list):
                    raise TypeError
                return "".join(lines)

            result_body = []
            if type_ == "keyword":
                logger.debug("this is keyword")
                result_body.append(get_header())
            else:
                result_body.append(get_header())
                body = []
                doc = docstring()
                if doc != "":
                    paragraphs = split_p(doc)
                    for par in paragraphs:
                        lines = split_br(par)
                        par_body = join_br(lines)
                        body.append(par_body)
                    result_body += wrap_p(body)
                    
            logger.debug(result_body)
            result = "".join(result_body)
        except Exception:
            logger.exception("some wrong", exc_info=True)
        finally:
            return result
