# pyglance: audit your python code

pyglance is a small, dependency-free static analyzer for Python code.

It reports:

- unused imports
- functions longer than 50 lines
- TODO and FIXME comments
- circular imports between local files

Requires Python 3.11 or newer. 

## Setup

1. Download or clone this project, then open a terminal in its root directory:

```text
cd path/to/pyglance
```

2. Install pyglance:

```text
python -m pip install .
```

If `pyglance` is not recognized, add the scripts directory reported by pip
to your `PATH` (this is the `Scripts` folder on Windows, or `bin` on macOS/Linux), then open a new terminal.

3. Analyze the current directory:

```text
pyglance
```

Or analyze another file or directory:

```text
pyglance path/to/project
```

Sample files are in `examples/`:

```text
pyglance examples
```

Directories are searched recursively for `.py` files. Virtual environments,
`__pycache__`, and build output are skipped.

Example output from `pyglance examples`:

```text
UNUSED_IMPORT unused.py:1 - 'json' imported but not used
LONG_FUNCTION long_function.py:1 - function 'handle_request' is 51 lines long
TODO todo.py:1 - TODO found: "refactor validation"
CIRCULAR_IMPORT a.py:1 -> b.py:1 -> a.py:1
```

Findings are written to standard output in a deterministic order. The process
exits with status 1 if anything was reported. Pass `--exit-zero` to always exit 0.

A file with a syntax error is skipped (the message goes to stderr) and the
rest of the tree is still checked.

Unused-import detection only looks for names loaded in the AST, so re-exports
and some other patterns can be reported incorrectly.