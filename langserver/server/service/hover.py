import html
hover_error = None


try:
    from jedi import Script, Project
except ModuleNotFoundError:
    completion_error = "jedi"


class Hover:
    def __init__(self, source, **kwargs):
        self.source = source
        settings = kwargs.get("settings", {})
        try:
            path = settings["jedi"]["project"]["path"]
        except KeyError:
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
            return None, str(e)

    def build_html_layout(self, data) -> str:
        type_ = data.type
        name = data.name
        if type_ == "keyword":
            return "<code>{} : {}</code>".format(type_, name)

        module_path = data.module_path if data.module_path else ""
        definition = "{}:{}:{}".format(module_path, data.line, data.column)
        doc = data.docstring()
        doc = html.escape(doc, quote=False)

        head = "<code>{} : <a href=\"{}\">{}</a></code>".format(
            type_, definition, name)

        doc_lines = doc.split("\n")
        title = doc_lines[0]
        title = "<h4>{}</h4>".format(title)
        body = doc_lines[1:]
        def wrap_p(line): return "<p>{}</p>".format(line)
        body = [wrap_p(line) for line in body]
        return "".join([head, title]+body)
