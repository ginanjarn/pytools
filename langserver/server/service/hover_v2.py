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

            if len(result) <= 0:
                return None
            prebuit_doc = self.build_html_layout(result[0])
            ret = {"contents": {"language": "html", "value": prebuit_doc}}
        except Exception:
            raise HoverError

        return ret

    def build_html_layout(self, data) -> str:
        result = ""
        try:
            doc_body_l = []

            type_ = data.type
            name = data.name
            if type_ == "keyword":
                result = "<code>{} : {}</code>".format(type_, name)
            try:
                module_path = data.module_path if data.module_path else ""
                definition = "{}:{}:{}".format(
                    module_path, data.line, data.column + 1)
                logger.debug(definition)
                module_name = data.module_name
                module_name = module_name + "." if module_name != "__main__" else ""
                f_doc_head = "<code>%s : <a href=\"%s\">%s%s</a></code>" % (
                    type_, definition, module_name, name)
                doc_body_l.append(f_doc_head)
            except Exception:
                logger.warning("empty definition", exc_info=True)

            def join_section(doc_section, spacer=" "):
                return spacer.join(doc_section.split("\n"))

            if type_ in ["function", "class"]:
                doc = data.docstring(raw=False)
                logger.debug(doc)
                if doc != "":
                    doc_sect = doc.split("\n\n")
                    if len(doc_sect) > 2:
                        snippet = join_section(doc_sect[0], spacer=" ")
                        doc_body_l.append("<p><code>%s</code></p>" % snippet)

                        doc_title = doc_sect[1]
                        doc_body_l.append("<h4>%s</h4>" % doc_title)

                        for d in doc_sect[2:]:
                            r = join_section(d, spacer="<br>")
                            doc_body_l.append("<p>%s</p>" % r)
                    else:
                        doc_title = doc_sect[0]
                        doc_body_l.append("<h4>%s</h4>" % doc_title)
            else:
                doc = data.docstring(raw=True)
                logger.debug(doc)
                if doc != "":
                    doc_sect = doc.split("\n\n")
                    doc_title = doc_sect[0]
                    doc_body_l.append("<h4>%s</h4>" % doc_title)

                    if len(doc_sect) > 1:
                        for d in doc_sect[1:]:
                            r = join_section(d, spacer="<br>")
                            doc_body_l.append("<p>%s</p>" % r)
            f_doc_body = "".join(doc_body_l)
            logger.debug(f_doc_body)
            result = f_doc_body
        except Exception:
            logger.exception("build_html_layout", exc_info=True)
        finally:
            return result
