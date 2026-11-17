#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The baseline checks of perftest_plot.py: the latest of the loaded jobs against the average of
the earlier ones, per scenario, for runtime, CPU and memory usage."""

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

import logging
import re
from collections.abc import Sequence
from datetime import date, timedelta
from statistics import fmean
from typing import NamedTuple

from tests.performance.reporting.performance_db import MeasurementsList, PerformanceData

logger = logging.getLogger(__name__)


class AverageValues(NamedTuple):
    avg_time: float
    avg_cpu: float
    avg_mem: float


class BaselineValues(NamedTuple):
    """The average of each metric over the earlier jobs, or None if none of them has it.

    A metric is checked only against a baseline above 0.
    """

    avg_time: float | None
    avg_cpu: float | None
    avg_mem: float | None


class SkippedScenario(NamedTuple):
    """Represents a scenario that should be skipped during validation.

    Attributes:
        pattern: A regex pattern to match the scenario name against.
        reason: Human-readable explanation for why the scenario is skipped.
        condition: Optional boolean indicating if the scenario should be skipped.
    """

    pattern: str
    reason: str
    condition: bool = True


class BaselineAlert(NamedTuple):
    """Represents a finding of the baseline validation.

    Attributes:
        message: Human-readable description of the finding.
        is_failure: Whether the finding should fail the job. Findings that merely report
            the absence of data are reported, but do not fail the job.
    """

    message: str
    is_failure: bool = True


class PerformanceBaselines:
    """Checks the latest of the loaded jobs against the baseline of the earlier ones."""

    def __init__(
        self,
        jobs: PerformanceData,
        job_names: Sequence[str],
        scenario_names: Sequence[str],
        cpu_usage_metric: str,
        memory_usage_metric: str,
        cpu_tolerance: float,
        mem_tolerance: float,
        runtime_tolerance: float,
        baseline_offset: int,
        today: date | None = None,
    ) -> None:
        self.jobs = jobs
        self.job_names = job_names
        self.scenario_names = scenario_names
        self.cpu_usage_metric = cpu_usage_metric
        self.memory_usage_metric = memory_usage_metric
        self.cpu_tolerance = cpu_tolerance
        self.mem_tolerance = mem_tolerance
        self.runtime_tolerance = runtime_tolerance
        self.baseline_offset = baseline_offset
        self.today = today or date.today()

    @staticmethod
    def _get_mean_value(measurements: MeasurementsList, metric_name: str) -> float:
        """
        Compute the arithmetic mean for a specified metric across a list of measurement records.

        Parameters:
            measurements : MeasurementsList
                Iterable / list of measurement rows containing the target metric.
            metric_name : str
                The key/name of the metric to extract from each measurement row.

        Returns:
            float
                The mean (floating-point) value of the metric across all measurements.
                Returns 0.0 if the input list is empty.
        """
        values: list[float] = [float(str(row[metric_name])) for row in measurements]
        return fmean(values or [0])

    def _calculate_baseline(self, scenario_name: str) -> BaselineValues:
        """
        Compute average (baseline) metrics for a given benchmark scenario across the loaded jobs
        before the latest one, which is the one checked against them.

        This method iterates over these jobs, searches their benchmark lists for the specified
        scenario and aggregates mean values for the execution time, the CPU usage and the memory
        usage.

        If a scenario is missing in a job, an error is logged and that job is skipped.
        If no values are collected for a metric, it has no baseline (None).

        Parameters:
            scenario_name : str
                The name of the benchmark scenario to aggregate across all jobs.

        Returns:
                BaselineValues
        """
        time_averages: list[float] = []
        cpu_averages: list[float] = []
        mem_averages: list[float] = []
        for job_name, job in self.jobs.items():
            if job_name == self.job_names[-1]:
                continue
            if not isinstance(benchmarks := job[0]["benchmarks"], list):
                continue
            benchmark = next((_ for _ in benchmarks if _["name"] == scenario_name), None)
            if not benchmark:
                logger.warning('Scenario "%s" not found in job "%s"!', scenario_name, job_name)
                continue
            time_averages.append(benchmark["stats"]["mean"])
            if scenario_name not in job[1]:
                continue
            if not (measurements := job[1][scenario_name]):
                continue
            cpu_averages.append(self._get_mean_value(measurements, self.cpu_usage_metric))
            mem_averages.append(self._get_mean_value(measurements, self.memory_usage_metric))
        return BaselineValues(
            avg_time=fmean(time_averages) if time_averages else None,
            avg_cpu=fmean(cpu_averages) if cpu_averages else None,
            avg_mem=fmean(mem_averages) if mem_averages else None,
        )

    def _current_averages(self, scenario_name: str) -> AverageValues | None:
        """
        Return averaged performance metrics for a given benchmark scenario of the most recent job.

        If the benchmarks collection is not a list, or the named scenario is not present,
        the method returns None.

        Parameters:
            scenario_name : str
                    The exact benchmark scenario name to search for in the most recent job.

        Returns:
            AverageValues | None
                    An AverageValues instance containing (time_avg, cpu_avg, mem_avg) if the
                    scenario is found; otherwise None.
        """
        job = self.jobs[self.job_names[-1]]
        benchmarks = job[0]["benchmarks"]
        if not isinstance(benchmarks, list):
            return None
        benchmark = next((_ for _ in benchmarks if _["name"] == scenario_name), None)
        if not benchmark:
            return None
        time_avg = benchmark["stats"]["mean"]
        cpu_avg = self._get_mean_value(job[1][scenario_name], self.cpu_usage_metric)
        mem_avg = self._get_mean_value(job[1][scenario_name], self.memory_usage_metric)

        return AverageValues(*(time_avg, cpu_avg, mem_avg))

    @staticmethod
    def _skipped_scenario(
        scenario_name: str,
        baseline_name: str,
        skipped_scenarios: list[SkippedScenario],
    ) -> bool:
        """
        Check if a scenario should be skipped based on pattern matching and an optional condition.

        Args:
            scenario_name: The name of the scenario to check.
            baseline_name: The name of the baseline being evaluated.
            skipped_scenarios: A list of SkippedScenario objects.

        Returns:
            True if the scenario should be skipped, False otherwise.
        """
        for skipped_scenario in skipped_scenarios:
            if re.fullmatch(skipped_scenario.pattern, scenario_name) and skipped_scenario.condition:
                logger.info(
                    "Ignoring baseline %s scenario %s due to %s.",
                    baseline_name,
                    scenario_name,
                    skipped_scenario.reason,
                )
                return True
        return False

    def validate_performance_baselines(self) -> list[BaselineAlert]:
        """
        Validate current performance metrics against calculated baselines for each test scenario.

        For every scenario the method retrieves the current averaged metrics (time, CPU, memory)
        and a computed baseline, then compares them using a fixed overshoot tolerance (+10%).

        An alert is generated when any of the following averaged metrics exceeds its baseline by
        more than the tolerance percentage:
            - Execution time (avg_time)
            - CPU usage (avg_cpu)
            - Memory usage (avg_mem)

        If no current data (averages) are available for a scenario, a non-failing alert is
        added: the scenario is reported, but a missing measurement is not a regression.

        Returns:
            list[BaselineAlert]
                A list of alerts in scenario order. The list is empty if all scenarios
                are within tolerated performance bounds.
        """
        cpu_tolerance = self.cpu_tolerance
        mem_tolerance = self.mem_tolerance
        runtime_tolerance = self.runtime_tolerance
        baseline_offset = self.baseline_offset
        baseline_name = {0: "weekly", 30: "monthly", 365: "yearly"}.get(
            baseline_offset, f"{baseline_offset}d"
        )
        baseline_date = self.today - timedelta(days=baseline_offset)

        skipped_scenarios = [
            SkippedScenario(pattern="test_performance_piggyback", reason="CMK-27171"),
            SkippedScenario(
                pattern="test_performance_ui_response_.*",
                reason="scenario changes on 2026-02-06",
                condition=baseline_date < date(2026, 2, 6),
            ),
        ]

        alerts: list[BaselineAlert] = []
        for scenario_name in self.scenario_names:
            if not scenario_name.startswith("test_"):
                continue
            if self._skipped_scenario(scenario_name, baseline_name, skipped_scenarios):
                continue

            msg_prefix = f"Scenario {scenario_name}: "
            msg_suffix = (
                f"; tolerance: +{cpu_tolerance}% CPU"
                f", +{mem_tolerance}% memory"
                f", +{runtime_tolerance}% time)"
            )
            averages = self._current_averages(scenario_name)
            if not averages:
                alerts.append(
                    BaselineAlert(
                        f"{msg_prefix}Missing data! Test aborted or skipped?", is_failure=False
                    )
                )
                continue
            baseline = self._calculate_baseline(scenario_name)
            # A metric without a baseline (None) is not checked. Neither is a baseline of 0: no
            # overshoot can be computed against it, so it is reported without failing.
            if zero_metrics := [
                metric
                for metric, value in (
                    ("execution time", baseline.avg_time),
                    ("CPU usage", baseline.avg_cpu),
                    ("memory usage", baseline.avg_mem),
                )
                if value == 0
            ]:
                alerts.append(
                    BaselineAlert(
                        f"{msg_prefix}{', '.join(zero_metrics)} baseline {baseline_name} is 0,"
                        " not checked",
                        is_failure=False,
                    )
                )
            if (
                baseline.avg_time
                and averages.avg_time > baseline.avg_time * (100 + runtime_tolerance) / 100
            ):
                overshoot = round((averages.avg_time / baseline.avg_time) * 100 - 100, 2)
                msg = (
                    f"Execution time baseline {baseline_name} exceeded by {overshoot}% "
                    f"(baseline: {round(baseline.avg_time, 2)};"
                    f" actual: {round(averages.avg_time, 2)}"
                )

                alerts.append(BaselineAlert(f"{msg_prefix}{msg}{msg_suffix}"))
            if (
                baseline.avg_cpu
                and averages.avg_cpu > baseline.avg_cpu * (100 + cpu_tolerance) / 100
            ):
                overshoot = round((averages.avg_cpu / baseline.avg_cpu) * 100 - 100, 2)
                msg = (
                    f"CPU usage baseline {baseline_name} exceeded by {overshoot}% "
                    f"(baseline: {round(baseline.avg_cpu, 2)}%;"
                    f" actual: {round(averages.avg_cpu, 2)}%"
                )
                alerts.append(BaselineAlert(f"{msg_prefix}{msg} {msg_suffix}"))
            if (
                baseline.avg_mem
                and averages.avg_mem > baseline.avg_mem * (100 + mem_tolerance) / 100
            ):
                overshoot = round((averages.avg_mem / baseline.avg_mem) * 100 - 100, 2)
                msg = (
                    f"Memory usage baseline {baseline_name} exceeded by {overshoot}% "
                    f"(baseline: {round(baseline.avg_mem, 2)}%;"
                    f" actual: {round(averages.avg_mem, 2)}%"
                )
                alerts.append(BaselineAlert(f"{msg_prefix}{msg}{msg_suffix}"))
        return alerts
