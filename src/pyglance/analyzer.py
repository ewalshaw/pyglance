import ast
import io
import re
import sys
import tokenize
from pathlib import Path

from .utils import display_path, find_files, module_name

MARKER_RE = re.compile(r"\b(TODO|FIXME)\b\s*:?\s*(.*)", re.IGNORECASE)

_UNUSED_IMPORT = 0
_LONG_FUNCTION = 1
_TODO = 2
_CIRCULAR_IMPORT = 3
_DEAD_CODE = 4
_TERMINATORS = (ast.Return, ast.Raise, ast.Break, ast.Continue)

ALL_CHECKS = frozenset({
    "UNUSED_IMPORT",
    "LONG_FUNCTION",
    "TODO",
    "CIRCULAR_IMPORT",
    "DEAD_CODE",
})
DEFAULT_MAX_FUNCTION_LINES = 50
_KIND_TO_CHECK = {
    _UNUSED_IMPORT: "UNUSED_IMPORT",
    _LONG_FUNCTION: "LONG_FUNCTION",
    _TODO: "TODO",
    _CIRCULAR_IMPORT: "CIRCULAR_IMPORT",
    _DEAD_CODE: "DEAD_CODE",
}


def _imports(tree: ast.AST, mod: str, path: Path, modules: dict[str, Path]):
    found = []
    package = mod if path.name == "__init__.py" else mod.rpartition(".")[0]

    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".") if package else []
                up = node.level - 1
                parts = parts[: len(parts) - up] if up <= len(parts) else []
                base = ".".join([*parts, *base.split(".")]) if base else ".".join(parts)

            for alias in node.names:
                child = ".".join(p for p in (base, alias.name) if p)
                if child in modules:
                    names.append(child)
                elif base:
                    names.append(base)

        for name in names:
            target = modules.get(name)
            if target is None and package:
                target = modules.get(f"{package}.{name}")
            if target is not None and target != path:
                found.append((target, node.lineno))

    return found


def _cycles(graph: dict[Path, dict[Path, int]], root: Path):
    cycles = {}

    def shown(path: Path) -> str:
        return display_path(path, root)

    def walk(start, node, path, lines):
        for target, line in graph[node].items():
            if target == start:
                nodes = path[:]
                edge_lines = [*lines, line]
                keys = [shown(p) for p in nodes]
                i = min(range(len(keys)), key=lambda n: keys[n:] + keys[:n])
                nodes = nodes[i:] + nodes[:i]
                edge_lines = edge_lines[i:] + edge_lines[:i]
                key = tuple(shown(p) for p in nodes)
                cycles[key] = (nodes, edge_lines)
            elif target not in path:
                walk(start, target, [*path, target], [*lines, line])

    for start in sorted(graph, key=shown):
        walk(start, start, [start], [])

    return [cycles[key] for key in sorted(cycles)]


def _stmt_terminates(stmt) -> bool:
    if isinstance(stmt, _TERMINATORS):
        return True
    if isinstance(stmt, ast.If) and stmt.orelse:
        return _body_terminates(stmt.body) and _body_terminates(stmt.orelse)
    return False


def _body_terminates(body) -> bool:
    return any(_stmt_terminates(stmt) for stmt in body)


def _dead_in(body, shown, found):
    ended = False
    for stmt in body:
        if ended:
            found.append((_DEAD_CODE, shown, stmt.lineno,
                          f"DEAD_CODE {shown}:{stmt.lineno} - unreachable code"))
            break
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                             ast.With, ast.AsyncWith)):
            _dead_in(stmt.body, shown, found)
        elif isinstance(stmt, (ast.If, ast.For, ast.AsyncFor, ast.While)):
            _dead_in(stmt.body, shown, found)
            _dead_in(stmt.orelse, shown, found)
        elif isinstance(stmt, (ast.Try, ast.TryStar)):
            _dead_in(stmt.body, shown, found)
            for handler in stmt.handlers:
                _dead_in(handler.body, shown, found)
            _dead_in(stmt.orelse, shown, found)
            _dead_in(stmt.finalbody, shown, found)
        elif isinstance(stmt, ast.Match):
            for case in stmt.cases:
                _dead_in(case.body, shown, found)
        if _stmt_terminates(stmt):
            ended = True


def _file_findings(
    path: Path,
    source: str,
    tree: ast.AST,
    root: Path,
    max_function_lines: int = DEFAULT_MAX_FUNCTION_LINES,
):
    shown = display_path(path, root)
    found = []
    used = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                if name not in used:
                    found.append((_UNUSED_IMPORT, shown, node.lineno,
                                  f"UNUSED_IMPORT {shown}:{node.lineno}"
                                  f" - '{name}' imported but not used"))
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname or alias.name
                if name not in used:
                    found.append((_UNUSED_IMPORT, shown, node.lineno,
                                  f"UNUSED_IMPORT {shown}:{node.lineno}"
                                  f" - '{name}' imported but not used"))

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = node.end_lineno - node.lineno + 1
            if length > max_function_lines:
                found.append((_LONG_FUNCTION, shown, node.lineno,
                              f"LONG_FUNCTION {shown}:{node.lineno}"
                              f" - function '{node.name}' is {length} lines long"))

    _dead_in(tree.body, shown, found)

    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        match = MARKER_RE.search(token.string)
        if not match:
            continue
        marker = match.group(1).upper()
        text = match.group(2).strip()
        found.append((_TODO, shown, token.start[0],
                      f'{marker} {shown}:{token.start[0]} - {marker} found: "{text}"'))

    return found


def analyze(
    target: Path,
    checks: frozenset[str] | None = None,
    max_function_lines: int = DEFAULT_MAX_FUNCTION_LINES,
) -> list[str]:
    """Return issue lines for Python files under target.

    checks selects which rule ids to run. None means all checks.
    """
    active = ALL_CHECKS if checks is None else checks
    files = find_files(target)
    root = target.parent if target.is_file() else target
    parsed = {}
    findings = []

    def shown(path: Path) -> str:
        return display_path(path, root)

    for path in files:
        try:
            with tokenize.open(path) as f:
                source = f.read()
            parsed[path] = (source, ast.parse(source, filename=str(path)))
        except (OSError, SyntaxError, UnicodeError) as exc:
            print(f"skip {shown(path)}: {exc}", file=sys.stderr)

    ok = list(parsed)
    for path in sorted(ok, key=shown):
        for item in _file_findings(
            path, *parsed[path], root, max_function_lines=max_function_lines
        ):
            if _KIND_TO_CHECK[item[0]] in active:
                findings.append(item)

    if "CIRCULAR_IMPORT" in active:
        modules = {module_name(path, root): path for path in ok}
        if (root / "__init__.py").is_file():
            modules.update({
                ".".join(p for p in (root.name, name) if p): path
                for name, path in list(modules.items())
            })

        graph = {path: {} for path in ok}
        canonical = {path: module_name(path, root) for path in ok}
        for path in ok:
            for imported, line in _imports(parsed[path][1], canonical[path], path, modules):
                previous = graph[path].get(imported)
                graph[path][imported] = line if previous is None else min(previous, line)
            graph[path] = dict(sorted(graph[path].items(), key=lambda item: shown(item[0])))

        for nodes, lines in _cycles(graph, root):
            parts = [f"{shown(path)}:{line}" for path, line in zip(nodes, lines)]
            parts.append(parts[0])
            findings.append((_CIRCULAR_IMPORT, shown(nodes[0]), lines[0],
                             f"CIRCULAR_IMPORT {' -> '.join(parts)}"))

    return [text for _, _, _, text in sorted(findings)]
