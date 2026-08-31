from pathlib import Path

_SKIP_DIRS = frozenset({
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".venv",
    ".eggs",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "venv",
})


def _ignored(path: Path) -> bool:
    return any(part in _SKIP_DIRS or part.endswith(".egg-info") for part in path.parts)


def find_files(path: Path) -> list[Path]:
    """Return Python files under path, skipping cache and env directories."""
    if path.is_file():
        return [path] if path.suffix == ".py" else []
    return sorted(p for p in path.rglob("*.py") if p.is_file() and not _ignored(p))


def display_path(path: Path, root: Path) -> str:
    """Return path relative to the analysis root, using forward slashes."""
    path = path.resolve()
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def module_name(path: Path, root: Path) -> str:
    """Return the dotted module name of path relative to root."""
    rel = path.resolve().relative_to(root.resolve()).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)
