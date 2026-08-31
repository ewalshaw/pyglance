import sys
from pathlib import Path

import pytest

from pyglance.__main__ import main
from pyglance.analyzer import analyze
from pyglance.utils import display_path, find_files


def test_unused_import(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("import os\nprint(1)\n", encoding="utf-8")
    findings = analyze(tmp_path)
    assert findings == ["UNUSED_IMPORT a.py:1 - 'os' imported but not used"]


def test_used_import_is_quiet(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("import json\njson.dumps({})\n", encoding="utf-8")
    assert analyze(tmp_path) == []


def test_unused_from_import(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("from os.path import join\nprint(1)\n", encoding="utf-8")
    findings = analyze(tmp_path)
    assert findings == ["UNUSED_IMPORT a.py:1 - 'join' imported but not used"]


def test_used_from_import_is_quiet(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("from json import dumps\ndumps({})\n", encoding="utf-8")
    assert analyze(tmp_path) == []


def test_unused_aliased_import(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("import json as js\nprint(1)\n", encoding="utf-8")
    findings = analyze(tmp_path)
    assert findings == ["UNUSED_IMPORT a.py:1 - 'js' imported but not used"]


def test_used_aliased_import_is_quiet(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("import json as js\njs.dumps({})\n", encoding="utf-8")
    assert analyze(tmp_path) == []


def test_long_function(tmp_path: Path) -> None:
    body = "def f():\n" + "    x = 1\n" * 50
    (tmp_path / "a.py").write_text(body, encoding="utf-8")
    findings = analyze(tmp_path)
    assert findings == ["LONG_FUNCTION a.py:1 - function 'f' is 51 lines long"]


def test_long_async_function(tmp_path: Path) -> None:
    body = "async def f():\n" + "    x = 1\n" * 50
    (tmp_path / "a.py").write_text(body, encoding="utf-8")
    findings = analyze(tmp_path)
    assert findings == ["LONG_FUNCTION a.py:1 - function 'f' is 51 lines long"]


def test_todo_comment(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("# TODO: refactor validation\nx = 1\n", encoding="utf-8")
    findings = analyze(tmp_path)
    assert findings == ['TODO a.py:1 - TODO found: "refactor validation"']


def test_fixme_comment(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("# FIXME: handle empty input\nx = 1\n", encoding="utf-8")
    findings = analyze(tmp_path)
    assert findings == ['FIXME a.py:1 - FIXME found: "handle empty input"']


def test_circular_import(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("import b\n\ndef ping():\n    return b.pong\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("import a\n\ndef pong():\n    return a.ping\n", encoding="utf-8")
    findings = analyze(tmp_path)
    assert findings == ["CIRCULAR_IMPORT a.py:1 -> b.py:1 -> a.py:1"]


def test_relative_circular_import(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a.py").write_text(
        "from . import b\n\ndef ping():\n    return b.pong\n", encoding="utf-8"
    )
    (pkg / "b.py").write_text(
        "from . import a\n\ndef pong():\n    return a.ping\n", encoding="utf-8"
    )
    findings = analyze(tmp_path)
    assert findings == ["CIRCULAR_IMPORT pkg/a.py:1 -> pkg/b.py:1 -> pkg/a.py:1"]


def test_syntax_error_is_skipped(tmp_path: Path, capsys) -> None:
    (tmp_path / "good.py").write_text("import os\nprint(1)\n", encoding="utf-8")
    (tmp_path / "bad.py").write_text("def (\n", encoding="utf-8")
    findings = analyze(tmp_path)
    err = capsys.readouterr().err
    assert findings == ["UNUSED_IMPORT good.py:1 - 'os' imported but not used"]
    assert "skip bad.py:" in err


def test_venv_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "junk.py").write_text("import unused_mod\n", encoding="utf-8")
    assert find_files(tmp_path) == [tmp_path / "ok.py"]
    assert analyze(tmp_path) == []


def test_display_path_is_relative_to_root(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "a.py"
    path.parent.mkdir()
    path.write_text("x = 1\n", encoding="utf-8")
    assert display_path(path, tmp_path) == "sub/a.py"


def test_exit_codes(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "a.py").write_text("import os\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["pyglance", str(tmp_path)])
    assert main() == 1
    monkeypatch.setattr(sys, "argv", ["pyglance", "--exit-zero", str(tmp_path)])
    assert main() == 0
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["pyglance", str(tmp_path)])
    assert main() == 0


def test_missing_path_exits(tmp_path: Path, monkeypatch, capsys) -> None:
    missing = tmp_path / "does-not-exist"
    monkeypatch.setattr(sys, "argv", ["pyglance", str(missing)])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert "path does not exist" in capsys.readouterr().err
