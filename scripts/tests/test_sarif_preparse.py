#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import sys
from pathlib import Path

import pytest
from sarif_preparse import load_all, main


def _report(results: list[dict[str, object]] | None) -> str:
    run: dict[str, object] = {"tool": {"driver": {"name": "ruff", "rules": []}}}
    if results is not None:
        run["results"] = results
    return json.dumps({"version": "2.1.0", "runs": [run]})


def _result(rule_id: str, message: str) -> dict[str, object]:
    return {
        "ruleId": rule_id,
        "level": "warning",
        "message": {"text": message},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": "cmk/foo.py"},
                    "region": {"startLine": 1},
                }
            }
        ],
    }


@pytest.fixture(name="report_tree")
def fixture_report_tree(tmp_path: Path) -> Path:
    root = tmp_path / "bazel-out"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg/foo.AspectRulesLintRuff.report").write_text(_report([_result("E501", "too long")]))
    (root / "pkg/bar.AspectRulesLintRuff.report").write_text(_report([_result("F401", "unused")]))
    (root / "pkg/empty.AspectRulesLintRuff.report").write_text("")
    (root / "pkg/broken.AspectRulesLintRuff.report").write_text("{not json")
    (root / "pkg/noresults.AspectRulesLintMypy.report").write_text(_report(None))
    (root / "pkg/unrelated.report").write_text(_report([_result("X", "ignored")]))
    return root


def test_only_lint_reports_with_results_are_loaded(
    report_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    loaded = load_all(report_tree)

    assert sorted(result["message"]["text"] for result in loaded.get_results()) == [
        "too long",
        "unused",
    ]
    err = capsys.readouterr().err
    assert "broken.AspectRulesLintRuff.report" in err
    assert "Skipped 1 reports without results" in err


def test_main_writes_a_combined_sarif_file(
    report_tree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "out.sarif"
    monkeypatch.setattr(
        sys, "argv", ["sarif_preparse.py", "--root_dir", str(report_tree), "--output", str(output)]
    )

    main()

    combined = json.loads(output.read_text())
    assert sorted(
        result["message"]["text"] for run in combined["runs"] for result in run["results"]
    ) == ["too long", "unused"]
