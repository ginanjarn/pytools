import html
import logging
hover_error = None

try:
    from jedi import Script, Project
except ModuleNotFoundError:
    completion_error = "jedi"

logging.basicConfig(format='%(levelname)s: %(asctime)s  %(name)s: %(message)s')
logger = logging.getLogger(__name__)


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
            type_ = data.type
            name = data.name
            if type_ == "keyword":
                return "<code>{} : {}</code>".format(type_, name)

            module_path = data.module_path if data.module_path else ""
            module_name = data.module_name
            definition = "{}:{}:{}".format(module_path, data.line, data.column)
            logger.debug(definition)
            doc = data.docstring()
            logger.debug(doc)
            doc = html.escape(doc, quote=False)

            # head = "<code>{} : <a href=\"{}\">{}</a></code>".format(
                # type_, definition, name)

            # doc_lines = doc.split("\n")
            # title = doc_lines[0]
            # title = "<h4>{}</h4>".format(title)
            # body = doc_lines[1:]
            # def wrap_p(line): return "<p>{}</p>".format(line)
            # def wrap_p_tab(line): return "<p style=\"margin-left: 1em\">{}</p>".format(line)
            # def mark(line): return wrap_p_tab(line) if line.startswith("    ") else wrap_p(line)
            # body = [mark(line) for line in body]
            # result = "".join([head, title]+body)
            # logger.debug(result)
            # return result
            doc_body = doc.split("\n\n")
            doc_body_l = []
            
            f_doc_head = "<code>%s : <a href=\"%s\">%s.%s</a></code>"%(type_,definition,module_name,name)
            doc_body_l.append(f_doc_head)
            doc_title = doc_body[0]
            f_doc_title = "<h4>%s</h4>"%doc_title
            doc_body_l.append(f_doc_title)
            if len(doc_body)>1:
                doc_content = doc_body[1:]
                for content in doc_content:
                    content_line = content.split("\n")
                    f_content = "<br>".join(content_line)
                f_doc_content = "<p>%s</p>"%f_content
                doc_body_l.append(f_doc_content)
            f_doc_body = "".join(doc_body_l)
            logger.debug(f_doc_body)
            return f_doc_body
        except Exception as e:
            logger.error(e)
            return ""
