import logging
completion_error = None

try:
    from jedi import Script, Project
except ModuleNotFoundError:
    completion_error = "jedi"


logging.basicConfig(format='%(levelname)s: %(asctime)s  %(name)s: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Completion:
    def __init__(self, source, **kwargs):
        self.source = source
        settings = kwargs.get("settings", {})
        try:
            path = settings["jedi"]["project"]["path"]
            logger.debug(path)
        except KeyError:
            logger.warning("invalid project settings",exc_info=True)
            path = ""

        self.project = Project(path=path)

    def complete(self, line: int, character: int) -> (any, any):
        try:
            c = Script(source=self.source, project=self.project)
            result = c.complete(line, character)
            completion_list = []
            for r in result:
                completion = {}
                completion["label"] = r.name_with_symbols
                completion["kind"] = r.type                
                completion_list.append(completion)
            return completion_list, None
        except ValueError as e:
            logger.error("completing error",exc_info=True)
            return None, str(e)
