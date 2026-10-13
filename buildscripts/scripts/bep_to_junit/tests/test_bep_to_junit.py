#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from bep_to_junit.__main__ import main


def _action_id(label: str, output: str) -> dict[str, object]:
    return {
        "actionCompleted": {
            "primaryOutput": output,
            "label": label,
            "configuration": {"id": "cfg"},
        }
    }


def _write_bep(path: Path, events: list[object]) -> None:
    lines = [json.dumps(event) if not isinstance(event, str) else event for event in events]
    path.write_text("\n".join(lines) + "\n")


def _suite(output_dir: Path, dirname: str) -> ET.Element:
    root = ET.parse(output_dir / dirname / "test.xml").getroot()
    suite = root.find("testsuite")
    assert suite is not None
    return suite


def test_build_failure_gets_error_with_action_stderr_and_duration(tmp_path: Path) -> None:
    stderr_file = tmp_path / "stderr.txt"
    stderr_file.write_text("compile error: missing semicolon\n")
    _write_bep(
        tmp_path / "bep.json",
        [
            {
                "id": {"targetCompleted": {"label": "//pkg/sub:broken_lib"}},
                "completed": {
                    "success": False,
                    "failureDetail": {"message": "Compilation failed\nsee above"},
                },
                "children": [
                    _action_id("//pkg/sub:broken_lib", "bazel-out/broken.o"),
                    {"targetCompleted": {"label": "//pkg/sub:other"}},
                ],
            },
            {
                "id": _action_id("//pkg/sub:broken_lib", "bazel-out/broken.o"),
                "action": {
                    "stderr": {"name": "stderr", "uri": stderr_file.as_uri()},
                    "startTime": "2026-01-01T10:00:00.1234567Z",
                    "endTime": "2026-01-01T10:00:02.6234567Z",
                },
            },
        ],
    )
    output_dir = tmp_path / "out"

    assert main([str(tmp_path / "bep.json"), str(output_dir)]) == 0

    suite = _suite(output_dir, "pkg_sub_broken_lib")
    testcase = suite.find("testcase")
    assert testcase is not None
    assert testcase.attrib == {"classname": "pkg.sub", "name": "broken_lib", "time": "2.500"}
    error = testcase.find("error")
    assert error is not None
    assert error.get("message") == "Compilation failed"
    assert error.text == "Compilation failed\nsee above"
    system_out = suite.find("system-out")
    assert system_out is not None
    assert system_out.text == "compile error: missing semicolon"


def test_test_failure_uses_test_log_and_attempt_duration(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    test_log = tmp_path / "test.log"
    test_log.write_text("assertion failed\n")
    _write_bep(
        tmp_path / "bep.json",
        [
            {
                "id": {"targetCompleted": {"label": "//pkg:unit"}},
                "completed": {"success": False},
            },
            {
                "id": {"testResult": {"label": "//pkg:unit"}},
                "testResult": {
                    "status": "FAILED",
                    "statusDetails": "exit code 1",
                    "testAttemptDurationMillis": "1500",
                    "testActionOutput": [
                        {"name": "test.xml", "uri": (tmp_path / "missing.xml").as_uri()},
                        {"name": "test.log", "uri": test_log.as_uri()},
                    ],
                },
            },
        ],
    )
    output_dir = tmp_path / "out"

    main([str(tmp_path / "bep.json"), str(output_dir)])

    assert capsys.readouterr().err.count("wrote ") == 1, (
        "a test that ran is reported once, not additionally as build failure"
    )
    suite = _suite(output_dir, "pkg_unit")
    testcase = suite.find("testcase")
    assert testcase is not None
    assert testcase.get("time") == "1.500"
    error = testcase.find("error")
    assert error is not None
    assert error.text == "exit code 1"
    system_out = suite.find("system-out")
    assert system_out is not None
    assert system_out.text == "assertion failed\n"


def test_defaults_apply_when_details_are_missing(tmp_path: Path) -> None:
    _write_bep(
        tmp_path / "bep.json",
        [
            {"id": {"targetCompleted": {"label": "//pkg:silent"}}, "completed": {"success": False}},
            {"id": {"testResult": {"label": "//pkg:flaky"}}, "testResult": {"status": "FAILED"}},
        ],
    )
    output_dir = tmp_path / "out"

    main([str(tmp_path / "bep.json"), str(output_dir)])

    build_case = _suite(output_dir, "pkg_silent").find("testcase")
    assert build_case is not None
    build_error = build_case.find("error")
    assert build_error is not None
    assert build_error.text == "FAILED TO BUILD"
    assert build_case.get("time") == "0.000"
    test_case = _suite(output_dir, "pkg_flaky").find("testcase")
    assert test_case is not None
    test_error = test_case.find("error")
    assert test_error is not None
    assert test_error.text == "FAILED"
    assert _suite(output_dir, "pkg_flaky").find("system-out") is None


def test_unrelated_events_and_noise_are_ignored(tmp_path: Path) -> None:
    _write_bep(
        tmp_path / "bep.json",
        [
            "",
            "not json at all",
            {"id": {"targetCompleted": {"label": "//pkg:ok"}}, "completed": {"success": True}},
            {
                "id": {"targetCompleted": {"label": "//pkg:skipped"}},
                "aborted": {"reason": "SKIPPED"},
            },
            {"id": {"testResult": {"label": "//pkg:passing"}}, "testResult": {"status": "PASSED"}},
            {"id": {"progress": {}}},
        ],
    )
    output_dir = tmp_path / "out"

    main([str(tmp_path / "bep.json"), str(output_dir)])

    assert list(output_dir.iterdir()) == []


def test_unreadable_and_non_file_uris_yield_empty_logs(tmp_path: Path) -> None:
    _write_bep(
        tmp_path / "bep.json",
        [
            {
                "id": {"targetCompleted": {"label": "//pkg:lib"}},
                "completed": {"success": False},
                "children": [_action_id("//pkg:lib", "a.o"), _action_id("//pkg:lib", "b.o")],
            },
            {
                "id": _action_id("//pkg:lib", "a.o"),
                "action": {
                    "stderr": {"uri": (tmp_path / "gone.txt").as_uri()},
                    "startTime": "garbage",
                    "endTime": "2026-01-01T10:00:00Z",
                },
            },
            {
                "id": _action_id("//pkg:lib", "b.o"),
                "action": {"stderr": {"uri": "bytestream://remote/blob"}},
            },
        ],
    )
    output_dir = tmp_path / "out"

    main([str(tmp_path / "bep.json"), str(output_dir)])

    suite = _suite(output_dir, "pkg_lib")
    assert suite.find("system-out") is None
    testcase = suite.find("testcase")
    assert testcase is not None
    assert testcase.get("time") == "0.000"


def test_missing_bep_file_is_a_usage_error(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main([str(tmp_path / "nope.json"), str(tmp_path / "out")])
    assert excinfo.value.code == 2
