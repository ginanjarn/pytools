# PYTOOLS

Lightweight python tools for **Sublime Text.**

## FEATURES

* **Code completion** . 
* **Hover help**.
* **PEP8 Format code**.
* **Lint package**.

## REQUIREMENTS

* `jedi`
* `black`
* `pylint`

## INSTALL

Clone `github.com/ginanjarn/pytools` in your sublime text package installation directory.

> On **SublimeText** menu click ***Preferences>BrowsePackage***.

## SETUP

1. Install required package
```bash
	pip install jedi black pylint
```
> Change `pip` to `conda` if use conda manager.

2. Config Sublime Text:

* Setup **python** manually by define:

> SublimeText:  Preferences > Browse Packages...
> Create `Pytools.sublime-settings` on User directory.

```json
{
	// at Pytools.sublime-settings
	"python" :"python",
	"path": "environment_path",
}
```

* Use **command palette** (`ctrl+shift+p`) run command `PyTools: Environment Setup` **>**  Select **conda** or **venv**  **>** input the *environment location path*.

> **Conda** automatically detect default anaconda installation in *home directory*. Input path if you install in custom path.

## COMMAND

|No|Command|Function|
|--|-------|--------|
|1|`Format Code`|auto format code|
|2|`Lint`|show code diagnostic such: error, warning or notice|
|3|`Environment Setup`|Setup conda or venv environment for current project|
|4|`Change Environment`|Change working environment|
|5|`Shutdown Server`|Shutdown server tools|
|6|`Open Terminal`|Open teminal in current working directory|

> Sublime unable to shutdown server tools on exit. You should shutdown manually or let server running on background.

## LINT

Hover on **marked line number** to show diagnostic  **message**.

## TROUBLESHOOT

* Make sure if [python environment](#setup) is defined in settings.
* Make sure if [required package](#requirements) installed.
* Try shutdown server with `Pytools: Shutdown Server` command.
* Try restart Sublime Text. *(Restart **required** if **raise ServerError** and **updates**)*.

## BUG REPORT

Report bug in this [github repository issues](https://github.com/ginanjarn/pytools/issues).  Show error log ``ctrl+shift+` ``