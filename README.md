# PYTOOLS (SUBLIME TEXT PYTHON TOOLS)

## FEATURES
* Code completion with `jedi`.
* Format code with `autopep8`.
* Lint package with `pylint`.
* **Conda** integration.

## INSTALL
Clone `github.com/ginanjarn/pytools` in your sublime text package installation directory.
>On **SublimeText** menu click ***Preferences>BrowsePackage***.

## SETUP
>**Python** automatically detected if ***anaconda/miniconda*** installed in `USER` path.

1. Config **python** manually by define:
~~~json
{
	// Pytools.sublime-settings
	"python":"python.exe",
	"env":"path_environment",
}
~~~
2. Use **command palette** (`ctrl+shift+p`) run command `PyTools: Conda Setup`. (*anaconda/miniconda required*)

## CONDA
* **Setup** conda environment in **command palette** with  `PyTools: Conda Setup`.
* **Change** conda environment in **command palette** with `PyTools: Conda Environment`.
>Settings for `python` and `env` will changed to current activated environment.

## TROUBLESHOOT
* Make sure if python is defined in settings.
* Anaconda/Miniconda required for conda environment.
* Required package:
	* Code completion with `jedi`.
	* Code formatting with `autopep8`.
	* Package lint with `pylint`.
* If code completion not working try to reset server by `PyTools: Reset Jedi` in command palette.