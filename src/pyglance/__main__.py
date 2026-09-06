import argparse
from pathlib import Path

from .analyzer import ALL_CHECKS, analyze
from .config import ConfigError, effective_max_function_lines, load_config

_CHECK_HELP = ", ".join(sorted(ALL_CHECKS))


def _parse_checks(value: str) -> list[str]:
    return [part.strip().upper() for part in value.split(",") if part.strip()]


def _parse_globs(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: {value!r}") from None
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _resolve_checks(
    parser: argparse.ArgumentParser,
    select: list[str] | None,
    ignore: list[str] | None,
) -> frozenset[str]:
    active = set(ALL_CHECKS)
    if select is not None:
        unknown = sorted({name for name in select if name not in ALL_CHECKS})
        if unknown:
            parser.error(
                f"unknown check id(s): {', '.join(unknown)} (choose from {_CHECK_HELP})"
            )
        active = set(select)
    if ignore is not None:
        unknown = sorted({name for name in ignore if name not in ALL_CHECKS})
        if unknown:
            parser.error(
                f"unknown check id(s): {', '.join(unknown)} (choose from {_CHECK_HELP})"
            )
        active -= set(ignore)
    return frozenset(active)


def _announce_config_filters(
    settings,
    select_from_cli: bool,
    ignore_from_cli: bool,
) -> None:
    if not settings.announce_select_ignore:
        return
    if settings.select is not None and not select_from_cli:
        print(f"select: {', '.join(sorted(settings.select))}")
    if settings.ignore is not None and not ignore_from_cli:
        print(f"ignore: {', '.join(sorted(settings.ignore))}")


def main() -> int:
    """Run pyglance from the command line."""
    parser = argparse.ArgumentParser(
        prog="pyglance",
        description="Find common issues in Python code.",
    )
    parser.add_argument("path", nargs="?", default=".",
                        help="Python file or directory to analyze (default: current directory)")
    parser.add_argument(
        "--select",
        metavar="IDS",
        default=None,
        help=f"comma-separated check ids to run (default: all). ids: {_CHECK_HELP}",
    )
    parser.add_argument(
        "--ignore",
        metavar="IDS",
        default=None,
        help="comma-separated check ids to skip (applied after --select)",
    )
    parser.add_argument(
        "--max-function-lines",
        metavar="N",
        type=_positive_int,
        default=None,
        help="report functions longer than N lines (default: 50, or [tool.pyglance])",
    )
    parser.add_argument(
        "--exclude",
        metavar="GLOBS",
        default=None,
        help="comma-separated globs to skip (relative to the analysis root)",
    )
    parser.add_argument("--exit-zero", action="store_true",
                        help="exit 0 even when findings are reported")
    args = parser.parse_args()
    path = Path(args.path)

    if not path.exists():
        parser.error(f"path does not exist: {path}")

    try:
        settings = load_config(path)
    except ConfigError as exc:
        parser.error(str(exc))

    select_from_cli = args.select is not None
    ignore_from_cli = args.ignore is not None
    select = _parse_checks(args.select) if select_from_cli else settings.select
    ignore = _parse_checks(args.ignore) if ignore_from_cli else settings.ignore
    exclude = (
        _parse_globs(args.exclude) if args.exclude is not None
        else (settings.exclude or [])
    )
    max_function_lines = effective_max_function_lines(
        args.max_function_lines, settings
    )
    checks = _resolve_checks(parser, select, ignore)

    _announce_config_filters(settings, select_from_cli, ignore_from_cli)

    try:
        findings = analyze(
            path,
            checks=checks,
            max_function_lines=max_function_lines,
            exclude=exclude,
        )
    except (OSError, SyntaxError, UnicodeError) as exc:
        parser.error(str(exc))

    for finding in findings:
        print(finding)
    return 0 if args.exit_zero or not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
