# pyglance: audit your python code

pyglance is a small, dependency-free static analyzer for Python code.

It reports:

- unused imports (`UNUSED_IMPORT`)
- functions longer than 50 lines (`LONG_FUNCTION`; override with `--max-function-lines`)
- TODO and FIXME comments (`TODO`)
- circular imports between local files (`CIRCULAR_IMPORT`)
- unreachable code after `return`, `raise`, `break`, `continue`, or an `if`/`elif`/`else` where every branch returns (`DEAD_CODE`)

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
DEAD_CODE dead.py:3 - unreachable code
```

Findings are written to standard output in a deterministic order. The process
exits with status 1 if anything was reported. Pass `--exit-zero` to always exit 0.

Limit which checks run with `--select` / `--ignore` (comma-separated ids).
`--ignore` is applied after `--select`. Example:

```text
pyglance --select UNUSED_IMPORT,DEAD_CODE
pyglance --ignore TODO,LONG_FUNCTION
```

Set the long-function threshold with `--max-function-lines N` (default: 50):

```text
pyglance --max-function-lines 100
```

A file with a syntax error is skipped (the message goes to stderr) and the
rest of the tree is still checked.

Unused-import detection only looks for names loaded in the AST, so re-exports
and some other patterns can be reported incorrectly.

Unreachable‑code detection treats `return`, `raise`, `break`, and `continue` as unconditional block terminators, and treats an `if/elif/else` as a terminator only when all branches end in a terminating statement.
