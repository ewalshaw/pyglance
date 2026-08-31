# Design

pyglance walks `.py` files, parses each with the stdlib `ast` module, and
runs four checks.

## Unused imports and long functions

Unused imports are names bound by `import` / `from ... import` that never
appear as a loaded `ast.Name`. Function length is `end_lineno - lineno + 1`,
including blank lines and comments inside the function.

## TODO comments

Comment tokens come from `tokenize`, not the AST, so markers inside strings
are ignored.

## Circular imports

Local imports become a directed graph of files. Cycles are found with DFS
from each node. The reported cycle is rotated so the lexicographically
smallest path comes first, which keeps output stable when the same loop is
found from different starts.

DFS is enough for small projects. Strongly connected components (for example
Tarjan) would scale better on a dense import graph.

## Paths

Reported paths are relative to the path you passed in, not the current
working directory.
