# Pytools
Lightweight python development assistant with powerful code completion, documentation, document formatting and diagnostic.

## Features

### 1. Completion
   Code faster with code completion assistant.

### 2. Documentation
   Show documentation on hover attribute and go to definition.

### 3. Document formatting
   Consistent code formatting using `black` formatter.

### 4. Diagnostic
   Find potential error quickly without running the code using `pyflakes`.

### 5. Open terminal
   Open terminal with python environment enabled.

## Requirements
* Sublime Text 4
* Python 3.8

Following package required
* Jedi
* Black
* Pyflakes

> Sublime Text 3 not working.

> Conda environment and system installed python, automatically detected. But if you use different distribution, you should manually input the `interpreter` path in `Pytools.sublime-settings`.

> Use appropriated interpreter to provide accurate completion and diagnostic.

## Installation
Clone https://github.com/ginanjarn/pytools to Sublime Text package directory.
> On window menu ->`Preferences`->`Browse Packages...`.

## Commands
List commands shown in command pallete.

Commands|Usage
--|--
`Pytools: Change interpreter`|change python interpreter
`Pytools: Run server`|run background engine
`Pytools: Shutdown server`|shutdown background engine
`Pytools: Format document`|format code
`Pytools: Publish diagnostic`|publish diagnostic to active document
`Pytools: Clean diagnostic`|clean diagnostic in active document
`Pytools: Open terminal`|open terminal
`Pytools: Open terminal here...`|open terminal in active file directory
`Pytools: Change terminal emulator`|change terminal emulator

> Background engine should running automatically while editing. But still running while close Sublime Text. You should shut it down manually.

## License
This project released with MIT license, see the LICENSE file.

## Notes
This project has much limitation, but optimized for low performance computer. This plugin developed and tested in Windows(R). I've not yet test in other platform. Please give me pull request for those platform.