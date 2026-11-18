#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
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
    jobs: PerformanceData,
    today: date = date(2026, 11, 17),
    baseline_offset: int = 0,
    checked_job_name: str | None = None,
    scenario_names: Sequence[str] | None = None,
) -> PerformanceBaselines:
    return PerformanceBaselines(
        jobs=jobs,
        job_names=list(jobs),
        scenario_names=(
            scenario_names
            if scenario_names is not None
            else sorted({name for _, samples in jobs.values() for name in samples})
        ),
        cpu_usage_metric=CPU,
        memory_usage_metric=MEMORY,
        cpu_tolerance=15.0,
        mem_tolerance=10.0,
        runtime_tolerance=10.0,
        baseline_offset=baseline_offset,
        today=today,
        checked_job_name=checked_job_name,
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


def test_the_latest_run_does_not_count_towards_its_own_baseline() -> None:
    baselines = _baselines(_jobs({"test_x": (1.0, 50.0, 40.0)}, {"test_x": (1.15, 50.0, 40.0)}))

    alerts = baselines.validate_performance_baselines()

    assert [alert.is_failure for alert in alerts] == [True]


def test_a_scenario_without_earlier_runs_raises_no_alert() -> None:
    baselines = _baselines(_jobs({}, {"test_x": (1.0, 50.0, 40.0)}))

    alerts = baselines.validate_performance_baselines()

    assert alerts == []


def test_a_baseline_of_zero_is_reported_without_failing() -> None:
    baselines = _baselines(_jobs({"test_x": (1.0, 0.0, 40.0)}, {"test_x": (1.0, 50.0, 40.0)}))

    alerts = baselines.validate_performance_baselines()

    assert [
        (alert.is_failure, "CPU usage baseline weekly is 0" in alert.message) for alert in alerts
    ] == [(False, True)]


def test_without_todays_run_the_previous_one_is_not_checked_again() -> None:
    baselines = _baselines(
        _jobs({"test_x": (1.0, 50.0, 40.0)}, {"test_x": (2.0, 50.0, 40.0)}),
        checked_job_name="2.6.0-2026.11.17.pro",
    )

    alerts = baselines.validate_performance_baselines()

    assert [(alert.is_failure, "not found" in alert.message) for alert in alerts] == [(False, True)]


def test_a_run_without_resource_samples_is_checked_for_its_runtime() -> None:
    jobs = _jobs({"test_x": (1.0, 50.0, 40.0)}, {"test_x": (2.0, 50.0, 40.0)})
    del jobs[list(jobs)[-1]][1]["test_x"]
    baselines = _baselines(jobs)

    alerts = baselines.validate_performance_baselines()

    assert [("Execution time" in alert.message, alert.is_failure) for alert in alerts] == [
        (True, True)
    ]


def test_a_scenario_missing_from_the_latest_run_is_reported_without_failing() -> None:
    baselines = _baselines(_jobs({"test_x": (1.0, 50.0, 40.0)}, {}))

    alerts = baselines.validate_performance_baselines()

    assert [alert.is_failure for alert in alerts] == [False]


def test_a_scenario_in_none_of_the_loaded_jobs_is_not_reported() -> None:
    baselines = _baselines(
        _jobs({"test_x": (1.0, 50.0, 40.0)}, {"test_x": (1.0, 50.0, 40.0)}),
        scenario_names=["test_renamed_long_ago", "test_x"],
    )

    alerts = baselines.validate_performance_baselines()

    assert alerts == []


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
            {"test_performance_ui_response[chromium-login]": (1.0, 50.0, 40.0)},
            {"test_performance_ui_response[chromium-login]": (2.0, 50.0, 40.0)},
        ),
        today=date(2026, 2, 10),
        baseline_offset=baseline_offset,
    )

    alerts = baselines.validate_performance_baselines()

    assert [alert.is_failure for alert in alerts] == failures
