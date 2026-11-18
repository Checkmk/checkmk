#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import sys
from pathlib import Path

import pytest

from tests.performance.reporting.performance_args import parse_args
from tests.performance.reporting.perftest_plot import PerftestPlot

JOB = "3.0.0-2026.11.18.pro"


def _job_dir_with_three_rounds(root: Path) -> Path:
    job_dir = root / JOB
    job_dir.mkdir()
    (job_dir / "benchmark.json").write_text(json.dumps({"benchmarks": []}))
    for number, sample in (("", "a"), (".1", "b"), (".2", "c")):
        (job_dir / f"test_x[p]{number}.resources.json").write_text(json.dumps([{"time": sample}]))
    return job_dir


def _plot(root: Path, monkeypatch: pytest.MonkeyPatch, *options: str) -> PerftestPlot:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "perftest_plot",
            f"--root-dir={root}",
            "--skip-database-reads",
            "--skip-database-writes",
            "--skip-graph-generation",
            *options,
            JOB,
        ],
    )
    return PerftestPlot(parse_args())


def test_the_rounds_of_a_scenario_are_read_as_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _job_dir_with_three_rounds(tmp_path)
    _, scenario_data = _plot(tmp_path, monkeypatch).jobs[JOB]
    assert scenario_data == {"test_x[p]": [{"time": "a"}, {"time": "b"}, {"time": "c"}]}


def test_writing_a_scenario_back_merges_its_rounds_into_one_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_dir = _job_dir_with_three_rounds(tmp_path)
    _plot(tmp_path, monkeypatch, "--write-json-files").write_performance_data()
    assert sorted(path.name for path in job_dir.glob("*.resources.json")) == [
        "test_x[p].resources.json"
    ]
    assert json.loads((job_dir / "test_x[p].resources.json").read_text()) == [
        {"time": "a"},
        {"time": "b"},
        {"time": "c"},
    ]


def test_a_dot_in_a_benchmark_name_becomes_a_hyphen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_dir = tmp_path / JOB
    job_dir.mkdir()
    (job_dir / "benchmark.json").write_text(json.dumps({"benchmarks": [{"name": "test_x[1.5]"}]}))
    (job_dir / "test_x[1-5].resources.json").write_text(json.dumps([{"time": "a"}]))
    benchmark_data, _ = _plot(tmp_path, monkeypatch).jobs[JOB]
    assert benchmark_data["benchmarks"] == [{"name": "test_x[1-5]"}]
