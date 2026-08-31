import argparse
from pathlib import Path

from .analyzer import analyze


def main() -> int:
    """Run pyglance from the command line."""
    parser = argparse.ArgumentParser(
        prog="pyglance",
        description="Find common issues in Python code.",
    )
    parser.add_argument("path", nargs="?", default=".",
                        help="Python file or directory to analyze (default: current directory)")
    parser.add_argument("--exit-zero", action="store_true",
                        help="exit 0 even when findings are reported")
    args = parser.parse_args()
    path = Path(args.path)

    if not path.exists():
        parser.error(f"path does not exist: {path}")

    try:
        findings = analyze(path)
    except (OSError, SyntaxError, UnicodeError) as exc:
        parser.error(str(exc))

    for finding in findings:
        print(finding)
    return 0 if args.exit_zero or not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
