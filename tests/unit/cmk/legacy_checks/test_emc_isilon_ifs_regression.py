#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks import emc_isilon_ifs as legacy_emc_isilon_ifs
from cmk.legacy_checks.emc_isilon_ifs import check_emc_isilon_ifs, discover_emc_isilon_ifs
from cmk.plugins.emc.agent_based.emc_isilon_ifs import parse_emc_isilon_ifs
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_LEVELS, FSBlock


@pytest.fixture(name="emc_isilon_ifs_regression_data")
def _emc_isilon_ifs_regression_data() -> StringTable:
    return [["615553001652224", "599743491129344"]]


@pytest.fixture(autouse=True)
def _value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(legacy_emc_isilon_ifs, "get_value_store", dict)


def _results_and_metrics(
    item: str, params: dict[str, object], parsed: FSBlock
) -> tuple[list[Result], list[Metric]]:
    output = list(check_emc_isilon_ifs(item, params, parsed))
    return (
        [r for r in output if isinstance(r, Result)],
        [m for m in output if isinstance(m, Metric)],
    )


class TestEmcIsilonIfsRegression:
    def test_parse_function(self, emc_isilon_ifs_regression_data: StringTable) -> None:
        assert parse_emc_isilon_ifs(emc_isilon_ifs_regression_data) == (
            "ifs",
            587037088,
            571959963,
            0,
        )

    def test_discovery_cluster(self, emc_isilon_ifs_regression_data: StringTable) -> None:
        parsed = parse_emc_isilon_ifs(emc_isilon_ifs_regression_data)
        assert parsed is not None
        assert list(discover_emc_isilon_ifs(parsed)) == [Service(item="Cluster")]

    def test_check_function_cluster_filesystem(
        self, emc_isilon_ifs_regression_data: StringTable
    ) -> None:
        parsed = parse_emc_isilon_ifs(emc_isilon_ifs_regression_data)
        assert parsed is not None
        results, metrics = _results_and_metrics("Cluster", dict(FILESYSTEM_DEFAULT_LEVELS), parsed)

        assert all(r.state is State.OK for r in results)

        summary = " ".join(r.summary for r in results if r.summary)
        assert "Used: 2.57%" in summary
        assert "14.4 TiB of 560 TiB" in summary

        metric_names = {m.name for m in metrics}
        assert {"fs_used", "fs_free", "fs_used_percent", "fs_size"} <= metric_names

        fs_used_percent = next(m for m in metrics if m.name == "fs_used_percent")
        assert abs(fs_used_percent.value - 2.5683428369691015) < 0.01
        warn, crit = fs_used_percent.levels
        assert warn is not None and crit is not None
        assert abs(warn - 80.0) < 0.01
        assert abs(crit - 90.0) < 0.01
        assert fs_used_percent.boundaries == (0.0, 100.0)


@pytest.mark.parametrize(
    "test_data, expected_parsed",
    [
        ([["615553001652224", "599743491129344"]], ("ifs", 587037088, 571959963, 0)),
        ([["1073741824000", "536870912000"]], ("ifs", 1024000, 512000, 0)),
        ([["107374182400", "1073741824"]], ("ifs", 102400, 1024, 0)),
    ],
)
def test_emc_isilon_ifs_parse_scenarios(
    test_data: StringTable, expected_parsed: tuple[str, int, int, int]
) -> None:
    assert parse_emc_isilon_ifs(test_data) == expected_parsed


@pytest.mark.parametrize(
    "total_bytes, avail_bytes, expected_usage_percent",
    [
        (615553001652224, 599743491129344, 2.5683428369691015),
        (1073741824000, 536870912000, 50.0),
        (1073741824000, 107374182400, 90.0),
        (1073741824000, 53687091200, 95.0),
    ],
)
def test_emc_isilon_ifs_usage_calculation(
    total_bytes: int, avail_bytes: int, expected_usage_percent: float
) -> None:
    parsed = parse_emc_isilon_ifs([[str(total_bytes), str(avail_bytes)]])
    assert parsed is not None

    _, metrics = _results_and_metrics("Cluster", dict(FILESYSTEM_DEFAULT_LEVELS), parsed)
    fs_used_percent = next(m for m in metrics if m.name == "fs_used_percent")
    assert abs(fs_used_percent.value - expected_usage_percent) < 0.01


def test_emc_isilon_ifs_custom_thresholds() -> None:
    parsed = parse_emc_isilon_ifs([["1073741824000", "107374182400"]])  # 90% usage
    assert parsed is not None

    results, _ = _results_and_metrics("Cluster", {"levels": (85.0, 95.0)}, parsed)
    assert any(r.state is State.WARN for r in results)


def test_emc_isilon_ifs_critical_threshold() -> None:
    parsed = parse_emc_isilon_ifs([["1073741824000", "53687091200"]])  # 95% usage
    assert parsed is not None

    results, _ = _results_and_metrics("Cluster", dict(FILESYSTEM_DEFAULT_LEVELS), parsed)
    assert any(r.state is State.CRIT for r in results)


def test_emc_isilon_ifs_empty_data() -> None:
    assert parse_emc_isilon_ifs([]) is None


def test_emc_isilon_ifs_bytes_conversion() -> None:
    parsed = parse_emc_isilon_ifs([["1073741824", "536870912"]])
    assert parsed == ("ifs", 1024, 512, 0)
