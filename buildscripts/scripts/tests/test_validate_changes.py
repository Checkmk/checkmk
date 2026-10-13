#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest
from validate_changes import main

STAGES_YAML = """
VARIABLES:
    - NAME: CHANGED_FILES_REL
      SH: "echo cmk/foo.py cmk/bar.py"
    - NAME: EMPTY
      SH: "true"
    - NAME: VOLATILE
      SH: "echo from-yaml"
    - NAME: MULTILINE
      SH: "printf 'one\\ntwo'"
      REPLACE_NEWLINES: "yes"

STAGES:
    - NAME: "Stage ${FOO}"
      DIR: "${FOO}"
      ENV_VARS:
          MY_VAR: "${CHANGED_FILES_REL}"
      SEC_VAR_LIST: [SECRET]
      GIT_FETCH_TAGS: true
      COMMAND: |
          echo first \\
              continued
          echo second
      RESULT_CHECK_TYPE: "JUNIT"
      RESULT_CHECK_FILE_PATTERN: "results/*.xml"
      JENKINS_TEST_RESULT_PATH: "results"
    - NAME: "Conditional"
      ONLY_WHEN_NOT_EMPTY: "EMPTY"
      TEXT_ON_SKIP: "nothing to do"
      COMMAND: "echo conditional"
    - NAME: "Multiline"
      COMMAND: "echo ${MULTILINE} ${VOLATILE}"
"""


def _run(argv: Sequence[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["validate_changes.py", *argv])
    main()


_ANSI_ESCAPES = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    """The output without the terminal colours"""
    return _ANSI_ESCAPES.sub("", text)


def _write_stages(tmp_path: Path, content: str = STAGES_YAML) -> Path:
    stages_file = tmp_path / "stages.yml"
    stages_file.write_text(content)
    return stages_file


def test_write_file_to_stdout_emits_expanded_stages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stages_file = _write_stages(tmp_path)

    _run(["--env", "FOO=foo", "--write-file", "-", str(stages_file)], monkeypatch)

    result = json.loads(capsys.readouterr().out)
    assert result["VARIABLES"]["CHANGED_FILES_REL"] == "cmk/foo.py cmk/bar.py"
    assert result["STAGES"][0] == {
        "NAME": "Stage foo",
        "DIR": "foo",
        "ENV_VAR_LIST": ["MY_VAR=cmk/foo.py cmk/bar.py"],
        "SEC_VAR_LIST": ["SECRET"],
        "GIT_FETCH_TAGS": True,
        "GIT_FETCH_NOTES": False,
        "COMMAND": "echo first continued;echo second;",
        "RESULT_CHECK_TYPE": "JUNIT",
        "RESULT_CHECK_FILE_PATTERN": "results/*.xml",
        "JENKINS_TEST_RESULT_PATH": "results",
    }


def test_write_file_writes_json_to_given_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stages_file = _write_stages(tmp_path)
    output = tmp_path / "out.json"

    _run(["-e", "FOO=foo", "-w", str(output), str(stages_file)], monkeypatch)

    assert json.loads(output.read_text())["STAGES"][2]["NAME"] == "Multiline"


def test_stage_with_empty_condition_variable_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stages_file = _write_stages(tmp_path)

    _run(["-e", "FOO=foo", "-w", "-", str(stages_file)], monkeypatch)

    conditional = json.loads(capsys.readouterr().out)["STAGES"][1]
    assert conditional == {
        "NAME": "Conditional",
        "SKIPPED": "Reason: nothing to do, Condition: EMPTY",
    }


def test_no_skip_activates_conditional_stages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stages_file = _write_stages(tmp_path)

    _run(["-e", "FOO=foo", "--no-skip", "-w", "-", str(stages_file)], monkeypatch)

    conditional = json.loads(capsys.readouterr().out)["STAGES"][1]
    assert "SKIPPED" not in conditional
    assert conditional["COMMAND"] == "echo conditional"


def test_command_line_variable_wins_over_yaml_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stages_file = _write_stages(tmp_path)

    _run(["-e", "FOO=foo", "-e", "VOLATILE=from-cli", "-w", "-", str(stages_file)], monkeypatch)

    result = json.loads(capsys.readouterr().out)
    assert result["VARIABLES"]["VOLATILE"] == "from-cli"


def test_replace_newlines_joins_multiline_command_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stages_file = _write_stages(tmp_path)

    _run(["-e", "FOO=foo", "-w", "-", str(stages_file)], monkeypatch)

    result = json.loads(capsys.readouterr().out)
    assert result["VARIABLES"]["MULTILINE"] == "one two"
    assert result["STAGES"][2]["COMMAND"] == "echo one two from-yaml"


def test_unexpanded_variable_in_stage_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stages_file = _write_stages(tmp_path)

    with pytest.raises(RuntimeError, match="unexpanded variables left in stage"):
        _run(["-w", "-", str(stages_file)], monkeypatch)


def test_unexpanded_variable_in_variable_command_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stages_file = _write_stages(
        tmp_path,
        "VARIABLES:\n  - NAME: X\n    SH: 'echo ${UNDEFINED}'\nSTAGES: []\n",
    )

    with pytest.raises(RuntimeError, match="unexpanded variables in command"):
        _run(["-w", "-", str(stages_file)], monkeypatch)


def test_missing_stages_file_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(RuntimeError, match="Could not find"):
        _run(["-w", "-", str(tmp_path / "missing.yml")], monkeypatch)


RUN_LOCALLY_YAML = """
VARIABLES:
    - NAME: EMPTY
      SH: "true"
STAGES:
    - NAME: "Succeeding"
      ENV_VARS:
          GREETING: "hello"
      COMMAND: "echo $GREETING && echo warning >&2"
    - NAME: "Skipped"
      ONLY_WHEN_NOT_EMPTY: "EMPTY"
      COMMAND: "echo never"
    - NAME: "Failing"
      RESULT_CHECK_FILE_PATTERN: "${RESULT_FILE}"
      COMMAND: "echo failure output && exit 1"
    - NAME: "Afterwards"
      COMMAND: "echo afterwards"
"""


def _run_locally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> str:
    stages_file = _write_stages(tmp_path, RUN_LOCALLY_YAML)
    result_file = tmp_path / "result.txt"
    result_file.write_text("first error line\nsecond error line\n")

    _run(["-e", f"RESULT_FILE={result_file}", str(stages_file)], monkeypatch)

    return _plain(capsys.readouterr().out)


def test_run_locally_reports_successful_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = _run_locally(tmp_path, monkeypatch, capsys)

    assert "Found 4 stage commands to run locally" in out
    assert "Stage 'Succeeding': SUCCESSFUL" in out


def test_run_locally_skips_stage_with_empty_condition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = _run_locally(tmp_path, monkeypatch, capsys)

    assert "Stage 'Skipped': SKIPPED Reason: not provided, Condition: EMPTY" in out
    assert "never" not in out


def test_run_locally_echoes_output_and_result_file_of_failed_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = _run_locally(tmp_path, monkeypatch, capsys)

    assert "Failing: failure output" in out
    assert f"Also a result file '{tmp_path / 'result.txt'}' has been captured:" in out
    assert ">>> first error line" in out
    assert ">>> second error line" in out
    assert "Stage 'Failing': FAILED" in out


def test_run_locally_continues_after_failed_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = _run_locally(tmp_path, monkeypatch, capsys)

    assert "Stage 'Afterwards': SUCCESSFUL" in out


def test_run_locally_verbose_streams_output_directly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stages_file = _write_stages(tmp_path, RUN_LOCALLY_YAML)

    _run(["-v", "-e", f"RESULT_FILE={tmp_path / 'result.log'}", str(stages_file)], monkeypatch)

    out = _plain(capsys.readouterr().out)
    assert "Succeeding: hello" in out
    assert "Succeeding: stderr: warning" in out


def test_exitfirst_stops_after_first_failing_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stages_file = _write_stages(tmp_path, RUN_LOCALLY_YAML)

    _run(["-x", "-e", f"RESULT_FILE={tmp_path / 'result.log'}", str(stages_file)], monkeypatch)

    out = _plain(capsys.readouterr().out)
    assert "Stage 'Failing' returned non-zero and you told me to stop" in out
    assert "Afterwards" not in out
