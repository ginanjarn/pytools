import html
import logging
hover_error = None

try:
    from jedi import Script, Project
except ModuleNotFoundError:
    completion_error = "jedi"

logger = logging.getLogger("hover")
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(levelname)s\t%(module)s: %(lineno)d\t%(message)s'))
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)


class Hover:
    def __init__(self, source, **kwargs):
        self.source = source
        settings = kwargs.get("settings", {})
        try:
            path = settings["jedi"]["project"]["path"]
            logger.debug(path)
        except KeyError:
            logger.error("invalid project settings", exc_info=True)
            path = ""

        self.project = Project(path=path)

    def hover(self, line: int, character: int) -> (any, any):
        try:
            c = Script(source=self.source, project=self.project)
            result = c.help(line, character)
            # print(result)
            if len(result) <= 0:
                return None, None
            prebuit_doc = self.build_html_layout(result[0])
            ret = {"contents": {"language": "html", "value": prebuit_doc}}
            return ret, None
        except ValueError as e:
            logger.error(e)
            return None, str(e)

    def build_html_layout(self, data) -> str:
        try:
            doc_body_l = []

            type_ = data.type
            name = data.name
            if type_ == "keyword":
                return "<code>{} : {}</code>".format(type_, name)
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
            return f_doc_body
        except Exception as e:
            logger.error(e)
            return ""
