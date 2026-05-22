#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.emc.agent_based.emc_isilon_cpu import (
    check_emc_isilon_cpu_utilization,
    discover_emc_isilon_cpu_utilization,
    parse_emc_isilon_cpu,
)


@pytest.fixture(name="string_table_normal")
def fixture_string_table_normal() -> Sequence[Sequence[str]]:
    return [["123", "234", "231", "567"]]


@pytest.fixture(name="string_table_low_usage")
def fixture_string_table_low_usage() -> Sequence[Sequence[str]]:
    return [["50", "30", "100", "20"]]


@pytest.fixture(name="string_table_empty")
def fixture_string_table_empty() -> Sequence[Sequence[str]]:
    return []


@pytest.fixture(name="string_table_zero_values")
def fixture_string_table_zero_values() -> Sequence[Sequence[str]]:
    return [["0", "0", "0", "0"]]


@pytest.fixture(name="string_table_multiple_lines")
def fixture_string_table_multiple_lines() -> Sequence[Sequence[str]]:
    return [
        ["123", "234", "231", "567"],
        ["200", "100", "150", "300"],
    ]


def _results_and_metrics(output: list[object]) -> tuple[list[Result], list[Metric]]:
    return (
        [r for r in output if isinstance(r, Result)],
        [m for m in output if isinstance(m, Metric)],
    )


def test_parse_emc_isilon_cpu_normal(string_table_normal: list[list[str]]) -> None:
    assert parse_emc_isilon_cpu(string_table_normal) == [["123", "234", "231", "567"]]


def test_parse_emc_isilon_cpu_empty(string_table_empty: list[list[str]]) -> None:
    assert parse_emc_isilon_cpu(string_table_empty) is None


def test_parse_emc_isilon_cpu_multiple_lines(
    string_table_multiple_lines: list[list[str]],
) -> None:
    assert parse_emc_isilon_cpu(string_table_multiple_lines) == [
        ["123", "234", "231", "567"],
        ["200", "100", "150", "300"],
    ]


def test_discover_emc_isilon_cpu_utilization(string_table_normal: list[list[str]]) -> None:
    parsed = parse_emc_isilon_cpu(string_table_normal)
    assert parsed is not None
    assert list(discover_emc_isilon_cpu_utilization(parsed)) == [Service()]


def test_check_emc_isilon_cpu_utilization_normal(
    string_table_normal: list[list[str]],
) -> None:
    parsed = parse_emc_isilon_cpu(string_table_normal)
    assert parsed is not None
    results, metrics = _results_and_metrics(list(check_emc_isilon_cpu_utilization({}, parsed)))

    summaries = [r.summary for r in results]
    assert "User: 35.70%" in summaries
    assert "System: 23.10%" in summaries
    assert "Interrupt: 56.70%" in summaries
    assert "Total: 115.50%" in summaries

    metric_values = {m.name: m.value for m in metrics}
    assert metric_values["user"] == pytest.approx(35.7)
    assert metric_values["system"] == pytest.approx(23.1)
    assert metric_values["interrupt"] == pytest.approx(56.7)


def test_check_emc_isilon_cpu_utilization_low_usage(
    string_table_low_usage: list[list[str]],
) -> None:
    parsed = parse_emc_isilon_cpu(string_table_low_usage)
    assert parsed is not None
    results, _ = _results_and_metrics(list(check_emc_isilon_cpu_utilization({}, parsed)))

    summaries = [r.summary for r in results]
    assert "User: 8.00%" in summaries
    assert "System: 10.00%" in summaries
    assert "Interrupt: 2.00%" in summaries
    assert "Total: 20.00%" in summaries


def test_check_emc_isilon_cpu_utilization_with_thresholds() -> None:
    parsed = parse_emc_isilon_cpu([["800", "200", "500", "300"]])
    assert parsed is not None
    results, _ = _results_and_metrics(
        list(check_emc_isilon_cpu_utilization({"util": (80.0, 90.0)}, parsed))
    )

    total_result = next(r for r in results if r.summary.startswith("Total:"))
    assert total_result.state is State.CRIT
    assert "Total: 180.00%" in total_result.summary


def test_check_emc_isilon_cpu_utilization_zero_values(
    string_table_zero_values: list[list[str]],
) -> None:
    parsed = parse_emc_isilon_cpu(string_table_zero_values)
    assert parsed is not None
    results, _ = _results_and_metrics(list(check_emc_isilon_cpu_utilization({}, parsed)))

    for r in results:
        assert r.state is State.OK
    summaries = [r.summary for r in results]
    for label in ("User", "System", "Interrupt", "Total"):
        assert f"{label}: 0%" in summaries


def test_check_emc_isilon_cpu_utilization_empty_data() -> None:
    assert not list(check_emc_isilon_cpu_utilization({}, []))


def test_check_emc_isilon_cpu_utilization_warning_threshold() -> None:
    # Total = 100% with warn=80, crit=120 should yield WARN
    parsed = parse_emc_isilon_cpu([["400", "100", "300", "200"]])
    assert parsed is not None
    results, _ = _results_and_metrics(
        list(check_emc_isilon_cpu_utilization({"util": (80.0, 120.0)}, parsed))
    )

    total_result = next(r for r in results if r.summary.startswith("Total:"))
    assert total_result.state is State.WARN
    assert "Total: 100.00%" in total_result.summary


def test_check_emc_isilon_cpu_utilization_performance_data() -> None:
    parsed = parse_emc_isilon_cpu([["100", "50", "75", "25"]])
    assert parsed is not None
    _, metrics = _results_and_metrics(list(check_emc_isilon_cpu_utilization({}, parsed)))

    metric_values = {m.name: m.value for m in metrics}
    assert metric_values["user"] == pytest.approx(15.0)
    assert metric_values["system"] == pytest.approx(7.5)
    assert metric_values["interrupt"] == pytest.approx(2.5)
