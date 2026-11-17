#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from datetime import date

import pytest

from tests.performance.reporting.performance_baselines import PerformanceBaselines
from tests.performance.reporting.performance_db import PerformanceData

CPU = "cpu_info.cpu_percent"
MEMORY = "memory_info.virtual_memory_percent"

#: A scenario's mean runtime in seconds, and its CPU and memory usage in percent.
Usage = tuple[float, float, float]


def _jobs(*runs: Mapping[str, Usage]) -> PerformanceData:
    """One job per run, oldest first, so the last run is the one checked."""
    return {
        f"2.6.0-2026.11.{10 + day:02d}.pro": (
            {
                "benchmarks": [
                    {"name": name, "stats": {"mean": runtime}}
                    for name, (runtime, _, _) in run.items()
                ]
            },
            {name: [{CPU: cpu, MEMORY: memory}] for name, (_, cpu, memory) in run.items()},
        )
        for day, run in enumerate(runs)
    }


def _baselines(
    jobs: PerformanceData, today: date = date(2026, 11, 17), baseline_offset: int = 0
) -> PerformanceBaselines:
    return PerformanceBaselines(
        jobs=jobs,
        job_names=list(jobs),
        scenario_names=sorted({name for _, samples in jobs.values() for name in samples}),
        cpu_usage_metric=CPU,
        memory_usage_metric=MEMORY,
        cpu_tolerance=15.0,
        mem_tolerance=10.0,
        runtime_tolerance=10.0,
        baseline_offset=baseline_offset,
        today=today,
    )


def test_a_run_within_the_tolerances_raises_no_alert() -> None:
    baselines = _baselines(_jobs({"test_x": (1.0, 50.0, 40.0)}, {"test_x": (1.05, 52.0, 41.0)}))

    alerts = baselines.validate_performance_baselines()

    assert alerts == []


@pytest.mark.parametrize(
    "latest, finding",
    [
        pytest.param((2.0, 50.0, 40.0), "Execution time baseline weekly exceeded", id="runtime"),
        pytest.param((1.0, 90.0, 40.0), "CPU usage baseline weekly exceeded", id="cpu"),
        pytest.param((1.0, 50.0, 80.0), "Memory usage baseline weekly exceeded", id="memory"),
    ],
)
def test_a_metric_beyond_its_tolerance_fails_the_check(latest: Usage, finding: str) -> None:
    baselines = _baselines(_jobs({"test_x": (1.0, 50.0, 40.0)}, {"test_x": latest}))

    alerts = baselines.validate_performance_baselines()

    assert [alert.is_failure for alert in alerts] == [True]
    assert finding in alerts[0].message


def test_a_scenario_missing_from_the_latest_run_is_reported_without_failing() -> None:
    baselines = _baselines(_jobs({"test_x": (1.0, 50.0, 40.0)}, {}))

    alerts = baselines.validate_performance_baselines()

    assert [alert.is_failure for alert in alerts] == [False]


def test_a_scenario_that_is_no_test_is_not_checked() -> None:
    baselines = _baselines(
        _jobs({"setup_single_site": (1.0, 50.0, 40.0)}, {"setup_single_site": (5.0, 90.0, 80.0)})
    )

    alerts = baselines.validate_performance_baselines()

    assert alerts == []


def test_a_scenario_with_a_known_issue_is_not_checked() -> None:
    baselines = _baselines(
        _jobs(
            {"test_performance_piggyback": (1.0, 50.0, 40.0)},
            {"test_performance_piggyback": (5.0, 90.0, 80.0)},
        )
    )

    alerts = baselines.validate_performance_baselines()

    assert alerts == []


@pytest.mark.parametrize(
    "baseline_offset, failures",
    [
        pytest.param(30, [], id="baseline before the change"),
        pytest.param(0, [True], id="baseline after the change"),
    ],
)
def test_a_changed_scenario_is_checked_only_against_baselines_after_its_change(
    baseline_offset: int, failures: list[bool]
) -> None:
    """The UI response scenarios changed on 2026-02-06, so older baselines do not compare."""
    baselines = _baselines(
        _jobs(
            {"test_performance_ui_response_login": (1.0, 50.0, 40.0)},
            {"test_performance_ui_response_login": (2.0, 50.0, 40.0)},
        ),
        today=date(2026, 2, 10),
        baseline_offset=baseline_offset,
    )

    alerts = baselines.validate_performance_baselines()

    assert [alert.is_failure for alert in alerts] == failures
