#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from pathlib import Path

import pytest
from collect_mypy import main

MYPY_OUTPUT = """\
cmk/foo.py:12:5: error: Incompatible return value type  [return-value]
cmk/foo.py:20:1: note: See https://mypy.readthedocs.io
Some unrelated line
Found 1 error in 1 file (checked 3 source files)
"""


def _run(argv: Sequence[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["collect_mypy.py", *argv])
    main()


def test_each_mypy_finding_becomes_a_failing_testcase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bin_root = tmp_path / "bin"
    (bin_root / "cmk/base").mkdir(parents=True)
    (bin_root / "cmk/base/lib.mypy_stdout").write_text(MYPY_OUTPUT)

    _run([str(bin_root)], monkeypatch)

    root = ET.fromstring(capsys.readouterr().out)
    assert root.attrib == {"tests": "2", "failures": "2"}
    suite = root.find("testsuite")
    assert suite is not None
    assert suite.get("name") == "cmk/base/lib"
    cases = suite.findall("testcase")
    assert [tc.get("name") for tc in cases] == ["cmk/foo.py:12:5:error", "cmk/foo.py:20:1:note"]
    failure = cases[0].find("failure")
    assert failure is not None
    assert failure.get("type") == "error"
    assert failure.text == "cmk/foo.py:12:5: Incompatible return value type  [return-value]"


def test_xml_metacharacters_in_messages_are_escaped_exactly_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    message = 'Argument 1 has incompatible type "list[int]"; expected <nothing> & more'
    bin_root = tmp_path / "bin"
    bin_root.mkdir()
    (bin_root / "lib.mypy_stdout").write_text(f"cmk/foo.py:3:1: error: {message}  [arg-type]\n")

    _run([str(bin_root)], monkeypatch)

    out = capsys.readouterr().out
    assert "&amp;lt;" not in out, "escaped by hand and again by ElementTree"
    failure = ET.fromstring(out).find("testsuite/testcase/failure")
    assert failure is not None
    assert failure.get("message") == f"{message}  [arg-type]"
    assert failure.text == f"cmk/foo.py:3:1: {message}  [arg-type]"


def test_clean_target_reports_single_passing_testcase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bin_root = tmp_path / "bin"
    bin_root.mkdir()
    (bin_root / "clean.mypy_stdout").write_text("Success: no issues found\n")

    _run([str(bin_root)], monkeypatch)

    root = ET.fromstring(capsys.readouterr().out)
    assert root.attrib == {"tests": "1", "failures": "0"}
    assert [tc.get("name") for tc in root.iter("testcase")] == ["no errors"]


def test_wrong_argument_count_exits_with_usage(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        _run([], monkeypatch)
    assert excinfo.value.code == 2

    assert "usage:" in capsys.readouterr().err


def test_missing_bin_directory_exits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        _run([str(tmp_path / "missing")], monkeypatch)
    assert excinfo.value.code == 2

    assert "not a directory" in capsys.readouterr().err
