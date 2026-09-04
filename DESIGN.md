# Design

pyglance walks `.py` files, parses each with the stdlib `ast` module, and
runs five checks. CLI `--select` / `--ignore` narrow that set; `TODO` covers
both TODO and FIXME comments.

## Unused imports and long functions

Unused imports are names bound by `import` / `from ... import` that never
appear as a loaded `ast.Name`. Function length is `end_lineno - lineno + 1`,
including blank lines and comments inside the function.

## TODO comments

Comment tokens come from `tokenize`, not the AST, so markers inside strings
are ignored.

## Dead code

The first statement after a terminator in the same block is reported as
unreachable. Terminators are `return`, `raise`, `break`, `continue`, and
an `if`/`elif`/`else` whose every branch terminates (`elif` is a nested
`If` in `orelse`, so the same both-sides check covers the chain). An
`if` with no `else` never ends the following code.

Nested bodies (`if`, loops, `try`, functions, `match`) are still walked
for inner dead statements.

## Circular imports

Local imports become a directed graph of files. Cycles are found with DFS
from each node. The reported cycle is rotated so the lexicographically
smallest path comes first, which keeps output stable when the same loop is
found from different starts. The graph is built only when `CIRCULAR_IMPORT`
is active.

DFS is enough for small projects. Strongly connected components (for example
Tarjan) would scale better on a dense import graph.

## Paths

Reported paths are relative to the path you passed in, not the current
working directory.
