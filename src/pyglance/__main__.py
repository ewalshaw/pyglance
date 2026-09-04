import argparse
from pathlib import Path

from .analyzer import ALL_CHECKS, analyze

_CHECK_HELP = ", ".join(sorted(ALL_CHECKS))


def _parse_checks(value: str) -> list[str]:
    return [part.strip().upper() for part in value.split(",") if part.strip()]


def _resolve_checks(
    parser: argparse.ArgumentParser,
    select: str | None,
    ignore: str | None,
) -> frozenset[str]:
    active = set(ALL_CHECKS)
    if select is not None:
        names = _parse_checks(select)
        unknown = sorted({name for name in names if name not in ALL_CHECKS})
        if unknown:
            parser.error(f"unknown check id(s): {', '.join(unknown)} (choose from {_CHECK_HELP})")
        active = set(names)
    if ignore is not None:
        names = _parse_checks(ignore)
        unknown = sorted({name for name in names if name not in ALL_CHECKS})
        if unknown:
            parser.error(f"unknown check id(s): {', '.join(unknown)} (choose from {_CHECK_HELP})")
        active -= set(names)
    return frozenset(active)


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
        help=f"comma-separated check ids to run (default: all). ids: {_CHECK_HELP}",
    )
    parser.add_argument(
        "--ignore",
        metavar="IDS",
        help="comma-separated check ids to skip (applied after --select)",
    )
    parser.add_argument("--exit-zero", action="store_true",
                        help="exit 0 even when findings are reported")
    args = parser.parse_args()
    path = Path(args.path)

    if not path.exists():
        parser.error(f"path does not exist: {path}")

    checks = _resolve_checks(parser, args.select, args.ignore)

    try:
        findings = analyze(path, checks=checks)
    except (OSError, SyntaxError, UnicodeError) as exc:
        parser.error(str(exc))

    for finding in findings:
        print(finding)
    return 0 if args.exit_zero or not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
