"""pyhton environment manager"""

# FIXME: I have'n test other than windows machine
#        please report if any problem

import os
import glob
from typing import Iterator, List

if os.name == "nt":
    PYTHON_EXECUTABLE = "python.exe"
    ACTIVATE_PATH = "Scripts\\activate.bat"
else:
    PYTHON_EXECUTABLE = "bin/python"
    ACTIVATE_PATH = "bin/activate"


def get_all_interpreter() -> Iterator[str]:
    """Get all interpreter

    Currently only find python interpreter in PATH and default conda install directory.
    Path may be duplicated caused by search in PATH and conda environment.
    """
    home = os.path.expanduser("~")

    # find conda
    conda = glob.glob(home + "/*conda*/" + PYTHON_EXECUTABLE)
    if conda:
        yield from iter(conda)
        conda_envs = glob.glob(home + "/*conda*/envs/*/" + PYTHON_EXECUTABLE)
        yield from iter(conda_envs)

    for path in os.environ["PATH"].split(os.pathsep):
        test_path = os.path.join(path, PYTHON_EXECUTABLE)
        if os.path.exists(test_path):
            yield test_path


def get_envs_activate_command(interpreter: str) -> str:
    """Get envs activate command"""

    # where python installed
    base_path = interpreter[: -len(PYTHON_EXECUTABLE)]

    # activate venv
    if os.path.exists(os.path.join(base_path, ACTIVATE_PATH)):
        return os.path.join(base_path, ACTIVATE_PATH)

    # activate conda envs
    home = os.path.expanduser("~")
    for path in glob.glob(home + "/*conda*/" + ACTIVATE_PATH):
        if interpreter.startswith(path[: -len(ACTIVATE_PATH)]):
            return f"{path} {base_path}"


def get_python_exec_command(interpreter: str, target="") -> List[str]:
    """Get python exec commands

    Return list of command to execute target with specific environment activated
    """

    activate = get_envs_activate_command(interpreter).split()
    return activate + ["&&", "python", target]
