#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from pathlib import Path

import pytest
from collect_rust_tests import main

LIBTEST_OUTPUT = """
running 3 tests
test config::tests::parses_defaults ... ok
test config::tests::rejects_garbage ... FAILED
test slow_test ... ignored

failures:

---- config::tests::rejects_garbage stdout ----
thread 'main' panicked at 'assertion failed'

failures:
    config::tests::rejects_garbage

test result: FAILED. 1 passed; 1 failed; 1 ignored
"""


def _bazel_test_xml(system_out: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<testsuites><testsuite name="x" tests="1"><testcase name="x">'
        f"<system-out><![CDATA[{system_out}]]></system-out>"
        "</testcase></testsuite></testsuites>\n"
    )


def _run(argv: Sequence[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["collect_rust_tests.py", *argv])
    main()


def test_rust_target_gets_one_testcase_per_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    testlogs = tmp_path / "testlogs"
    rust_dir = testlogs / "packages/agent/test-713312421/unit_tests"
    rust_dir.mkdir(parents=True)
    (rust_dir / "test.xml").write_text(_bazel_test_xml(LIBTEST_OUTPUT))
    output = tmp_path / "out"

    _run([str(testlogs), str(output)], monkeypatch)

    suite = ET.parse(output / "packages/agent/unit_tests/test.xml").getroot().find("testsuite")
    assert suite is not None
    assert suite.attrib == {
        "name": "packages/agent/unit_tests",
        "tests": "3",
        "failures": "1",
        "errors": "0",
        "skipped": "1",
    }
    cases = {tc.get("name"): tc for tc in suite.findall("testcase")}
    assert cases["config::tests::parses_defaults"].get("classname") == "config::tests"
    assert cases["slow_test"].get("classname") == "packages/agent/unit_tests"
    assert cases["slow_test"].find("skipped") is not None
    failure = cases["config::tests::rejects_garbage"].find("failure")
    assert failure is not None
    assert failure.text == "thread 'main' panicked at 'assertion failed'"


def test_rust_target_without_tests_reports_placeholder_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    testlogs = tmp_path / "testlogs"
    (testlogs / "empty").mkdir(parents=True)
    (testlogs / "empty/test.xml").write_text(_bazel_test_xml("\nrunning 0 tests\n\n"))

    _run([str(testlogs), str(tmp_path / "out")], monkeypatch)

    suite = ET.parse(tmp_path / "out/empty/test.xml").getroot().find("testsuite")
    assert suite is not None
    assert suite.get("tests") == "1"
    assert [tc.get("name") for tc in suite.findall("testcase")] == ["no tests"]


def test_failed_test_without_captured_output_gets_default_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    testlogs = tmp_path / "testlogs"
    (testlogs / "t").mkdir(parents=True)
    (testlogs / "t/test.xml").write_text(_bazel_test_xml("running 1 test\ntest a::b ... FAILED\n"))

    _run([str(testlogs), str(tmp_path / "out")], monkeypatch)

    failure = ET.parse(tmp_path / "out/t/test.xml").getroot().find(".//failure")
    assert failure is not None
    assert failure.text == "Test failed (no output captured)"


def test_non_rust_and_unparsable_logs_are_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    testlogs = tmp_path / "testlogs"
    for name, content in (
        ("pytest", _bazel_test_xml("collected 3 items\n")),
        ("broken", "<not xml"),
        ("no_output", "<testsuites><testsuite/></testsuites>"),
    ):
        (testlogs / name).mkdir(parents=True)
        (testlogs / name / "test.xml").write_text(content)
    output = tmp_path / "out"

    _run([str(testlogs), str(output)], monkeypatch)

    assert list(output.rglob("test.xml")) == []


def test_wrong_argument_count_exits_with_usage(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        _run(["only-one"], monkeypatch)
    assert excinfo.value.code == 2

    assert "usage:" in capsys.readouterr().err


def test_missing_testlogs_directory_exits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        _run([str(tmp_path / "missing"), str(tmp_path / "out")], monkeypatch)
    assert excinfo.value.code == 2

    assert "not a directory" in capsys.readouterr().err
