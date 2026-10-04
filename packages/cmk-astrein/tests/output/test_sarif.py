#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import pytest

from cmk.astrein.framework import CheckerError
from cmk.astrein.output.sarif import format_sarif

_SUMMARIES = {"cmk-module-layer-violation": "Enforces layers"}


def _make_error(
    message: str = "Test error",
    line: int = 1,
    column: int = 0,
    file_path: str = "test.py",
    checker_id: str = "test-checker",
) -> CheckerError:
    """Helper to create CheckerError instances."""
    return CheckerError(
        message=message,
        line=line,
        column=column,
        file_path=Path(file_path),
        checker_id=checker_id,
    )


def test_empty_errors_list() -> None:
    result = format_sarif([], _SUMMARIES)
    data = json.loads(result)

    assert data["version"] == "2.1.0"
    assert len(data["runs"]) == 1
    assert data["runs"][0]["tool"]["driver"]["name"] == "astrein"
    assert data["runs"][0]["results"] == []
    assert data["runs"][0]["tool"]["driver"]["rules"] == []


def test_single_error() -> None:
    error = _make_error(
        message="Import not allowed",
        line=10,
        column=5,
        file_path="cmk/gui/test.py",
        checker_id="cmk-module-layer-violation",
    )
    result = format_sarif([error], _SUMMARIES)
    data = json.loads(result)

    assert len(data["runs"][0]["results"]) == 1
    result_item = data["runs"][0]["results"][0]
    assert result_item["ruleId"] == "cmk-module-layer-violation"
    assert result_item["level"] == "error"
    assert result_item["message"]["text"] == "Import not allowed"

    location = result_item["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "cmk/gui/test.py"
    assert location["region"]["startLine"] == 10
    assert location["region"]["startColumn"] == 6  # 0-based column 5 -> 1-based column 6


def test_multiple_errors_same_rule() -> None:
    errors = [
        _make_error(message="Error 1", line=5, checker_id="test-rule"),
        _make_error(message="Error 2", line=10, checker_id="test-rule"),
        _make_error(message="Error 3", line=15, checker_id="test-rule"),
    ]
    result = format_sarif(errors, _SUMMARIES)
    data = json.loads(result)

    assert len(data["runs"][0]["results"]) == 3
    assert len(data["runs"][0]["tool"]["driver"]["rules"]) == 1
    assert data["runs"][0]["tool"]["driver"]["rules"][0]["id"] == "test-rule"


def test_multiple_errors_different_rules() -> None:
    errors = [
        _make_error(checker_id="rule-a"),
        _make_error(checker_id="rule-b"),
        _make_error(checker_id="rule-c"),
        _make_error(checker_id="rule-a"),
    ]
    result = format_sarif(errors, _SUMMARIES)
    data = json.loads(result)

    assert len(data["runs"][0]["results"]) == 4
    rules = data["runs"][0]["tool"]["driver"]["rules"]
    assert len(rules) == 3
    rule_ids = [rule["id"] for rule in rules]
    assert sorted(rule_ids) == ["rule-a", "rule-b", "rule-c"]


def test_column_offset_conversion() -> None:
    error = _make_error(column=0)
    result = format_sarif([error], _SUMMARIES)
    data = json.loads(result)

    region = data["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]
    assert region["startColumn"] == 1


def test_column_offset_nonzero() -> None:
    error = _make_error(column=42)
    result = format_sarif([error], _SUMMARIES)
    data = json.loads(result)

    region = data["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]
    assert region["startColumn"] == 43


def test_file_path_formatting() -> None:
    error = _make_error(file_path="cmk/base/config.py")
    result = format_sarif([error], _SUMMARIES)
    data = json.loads(result)

    artifact_location = data["runs"][0]["results"][0]["locations"][0]["physicalLocation"][
        "artifactLocation"
    ]
    assert artifact_location["uri"] == "cmk/base/config.py"
    assert artifact_location["uriBaseId"] == "%SRCROOT%"


def test_sarif_schema_present() -> None:
    result = format_sarif([], _SUMMARIES)
    data = json.loads(result)

    assert "$schema" in data
    assert "sarif-schema-2.1.0.json" in data["$schema"]


def test_tool_metadata() -> None:
    result = format_sarif([], _SUMMARIES)
    data = json.loads(result)

    driver = data["runs"][0]["tool"]["driver"]
    assert driver["name"] == "astrein"
    assert driver["informationUri"] == "https://checkmk.com"
    assert driver["version"] == "1.0.0"


def test_valid_json_output() -> None:
    errors = [
        _make_error(message="Error 1"),
        _make_error(message="Error 2"),
    ]
    result = format_sarif(errors, _SUMMARIES)

    json.loads(result)


def test_json_indentation() -> None:
    result = format_sarif([], _SUMMARIES)

    assert "\n" in result
    assert "  " in result


@pytest.mark.parametrize(
    "checker_id, expected",
    [
        ("cmk-module-layer-violation", "Enforces layers"),
        ("unknown-rule-xyz", "Checker rule: unknown-rule-xyz"),
    ],
)
def test_rule_short_description(checker_id: str, expected: str) -> None:
    data = json.loads(format_sarif([_make_error(checker_id=checker_id)], _SUMMARIES))

    rule = data["runs"][0]["tool"]["driver"]["rules"][0]
    assert rule["shortDescription"]["text"] == expected


def test_full_sarif_structure_with_real_error() -> None:
    """Test complete SARIF structure with realistic error."""
    error = _make_error(
        message="Import of cmk.gui.pages not allowed in 'cmk.ccc'",
        line=25,
        column=10,
        file_path="cmk/ccc/version.py",
        checker_id="cmk-module-layer-violation",
    )
    result = format_sarif([error], _SUMMARIES)
    data = json.loads(result)

    assert data["$schema"]
    assert data["version"] == "2.1.0"
    assert len(data["runs"]) == 1

    run = data["runs"][0]

    assert run["tool"]["driver"]["name"] == "astrein"
    assert len(run["tool"]["driver"]["rules"]) == 1

    rule = run["tool"]["driver"]["rules"][0]
    assert rule["id"] == "cmk-module-layer-violation"
    assert "shortDescription" in rule

    assert len(run["results"]) == 1
    result_item = run["results"][0]
    assert result_item["ruleId"] == "cmk-module-layer-violation"
    assert result_item["level"] == "error"
    assert result_item["message"]["text"] == "Import of cmk.gui.pages not allowed in 'cmk.ccc'"

    location = result_item["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "cmk/ccc/version.py"
    assert location["artifactLocation"]["uriBaseId"] == "%SRCROOT%"
    assert location["region"]["startLine"] == 25
    assert location["region"]["startColumn"] == 11


def test_mixed_checkers_in_one_report() -> None:
    """Test SARIF output with errors from multiple different checkers."""
    errors = [
        _make_error(
            message="Import not allowed",
            checker_id="cmk-module-layer-violation",
            line=10,
        ),
        _make_error(
            message="Use literal string",
            checker_id="localization-checker",
            line=20,
        ),
        _make_error(
            message="Cannot read file",
            checker_id="file-read-error",
            line=1,
        ),
    ]
    result = format_sarif(errors, _SUMMARIES)
    data = json.loads(result)

    rules = data["runs"][0]["tool"]["driver"]["rules"]
    assert len(rules) == 3

    rule_ids = {rule["id"] for rule in rules}
    assert rule_ids == {
        "cmk-module-layer-violation",
        "localization-checker",
        "file-read-error",
    }

    assert len(data["runs"][0]["results"]) == 3


def test_rules_sorted_alphabetically() -> None:
    """Test that rules are sorted by ID for consistent output."""
    errors = [
        _make_error(checker_id="zebra-rule"),
        _make_error(checker_id="alpha-rule"),
        _make_error(checker_id="beta-rule"),
    ]
    result = format_sarif(errors, _SUMMARIES)
    data = json.loads(result)

    rules = data["runs"][0]["tool"]["driver"]["rules"]
    rule_ids = [rule["id"] for rule in rules]
    assert rule_ids == ["alpha-rule", "beta-rule", "zebra-rule"]
