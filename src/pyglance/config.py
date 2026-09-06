from dataclasses import dataclass
from pathlib import Path

import tomllib

from .analyzer import ALL_CHECKS, DEFAULT_MAX_FUNCTION_LINES

_KNOWN_KEYS = frozenset({
    "max-function-lines",
    "select",
    "ignore",
    "exclude",
    "announce-select-ignore",
})


class ConfigError(Exception):
    """Invalid or unreadable [tool.pyglance] configuration."""


@dataclass(frozen=True)
class Settings:
    max_function_lines: int | None = None
    select: list[str] | None = None
    ignore: list[str] | None = None
    exclude: list[str] | None = None
    announce_select_ignore: bool = True


def _check_ids(value: object, key: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{key} must be a list of strings")
    names = [item.strip().upper() for item in value]
    if any(not name for name in names):
        raise ConfigError(f"{key} entries must be non-empty check ids")
    unknown = sorted({name for name in names if name not in ALL_CHECKS})
    if unknown:
        known = ", ".join(sorted(ALL_CHECKS))
        raise ConfigError(
            f"unknown check id(s) in {key}: {', '.join(unknown)} (choose from {known})"
        )
    return names


def _exclude_patterns(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError("exclude must be a list of strings")
    patterns = [item.strip() for item in value]
    if any(not pattern for pattern in patterns):
        raise ConfigError("exclude entries must be non-empty")
    return patterns


def _parse_tool_table(table: dict) -> Settings:
    unknown = sorted(set(table) - _KNOWN_KEYS)
    if unknown:
        raise ConfigError(f"unknown key(s) in [tool.pyglance]: {', '.join(unknown)}")

    max_function_lines = None
    if "max-function-lines" in table:
        raw = table["max-function-lines"]
        if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
            raise ConfigError("max-function-lines must be a positive integer")
        max_function_lines = raw

    select = _check_ids(table["select"], "select") if "select" in table else None
    ignore = _check_ids(table["ignore"], "ignore") if "ignore" in table else None
    exclude = _exclude_patterns(table["exclude"]) if "exclude" in table else None

    announce_select_ignore = True
    if "announce-select-ignore" in table:
        raw = table["announce-select-ignore"]
        if not isinstance(raw, bool):
            raise ConfigError("announce-select-ignore must be a boolean")
        announce_select_ignore = raw

    return Settings(
        max_function_lines=max_function_lines,
        select=select,
        ignore=ignore,
        exclude=exclude,
        announce_select_ignore=announce_select_ignore,
    )


def load_config(start: Path) -> Settings:
    """Load [tool.pyglance] from the nearest pyproject.toml above start."""
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        path = directory / "pyproject.toml"
        if not path.is_file():
            continue
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ConfigError(f"cannot read {path.as_posix()}: {exc}") from exc

        tool = data.get("tool")
        if not isinstance(tool, dict) or "pyglance" not in tool:
            continue
        table = tool["pyglance"]
        if not isinstance(table, dict):
            raise ConfigError("[tool.pyglance] must be a table")
        return _parse_tool_table(table)
    return Settings()


def effective_max_function_lines(cli: int | None, settings: Settings) -> int:
    if cli is not None:
        return cli
    if settings.max_function_lines is not None:
        return settings.max_function_lines
    return DEFAULT_MAX_FUNCTION_LINES
