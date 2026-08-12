#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping

import pytest

import cmk.plugins.collection.agent_based.cpu_utilization_os as cpu_utilization_os_plugin
from cmk.agent_based.v1 import GetRateError
from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.collection.agent_based.cpu_utilization_os import (
    check_cpu_utilization_os,
    discover_cpu_utilization_os,
)
from cmk.plugins.lib.cpu_utilization_os import SectionCpuUtilizationOs

_SECTION = SectionCpuUtilizationOs(time_base=100.0, num_cpus=4, time_cpu=10.0)


def test_discover_cpu_utilization_os() -> None:
    assert list(discover_cpu_utilization_os(_SECTION)) == [Service()]


def test_check_cpu_utilization_os_first_call_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # First invocation has no prior counter value -> get_rate raises.
    value_store: dict[str, tuple[float, float]] = {}
    monkeypatch.setattr(cpu_utilization_os_plugin, "get_value_store", lambda: value_store)
    with pytest.raises(GetRateError):
        list(check_cpu_utilization_os({}, _SECTION))


@pytest.mark.parametrize(
    "params, second_time_cpu, expected_results",
    [
        pytest.param(
            {"util": (80.0, 90.0)},
            15.0,
            [
                Result(state=State.OK, summary="Total CPU: 50.00%"),
                Metric("util", 50.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="ok_below_warn",
        ),
        pytest.param(
            {"util": (80.0, 90.0)},
            19.5,
            [
                Result(
                    state=State.CRIT,
                    summary="Total CPU: 95.00% (warn/crit at 80.00%/90.00%)",
                ),
                Metric("util", 95.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="crit_above_crit",
        ),
    ],
)
def test_check_cpu_utilization_os_levels(
    params: Mapping[str, tuple[float, float]],
    second_time_cpu: float,
    expected_results: CheckResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cpu_utilization_os_plugin,
        "get_value_store",
        lambda: {"util": (_SECTION.time_base, _SECTION.time_cpu)},
    )

    # Measure: t=110s -> 10 seconds elapsed; delta cpu controls util.
    section_t1 = SectionCpuUtilizationOs(time_base=110.0, num_cpus=4, time_cpu=second_time_cpu)
    assert list(check_cpu_utilization_os(params, section_t1)) == expected_results


def test_check_cpu_utilization_os_high_load_duration_uses_wall_clock_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value_store: dict[str, object] = {"util": (0.0, 0.0)}
    monkeypatch.setattr(cpu_utilization_os_plugin, "get_value_store", lambda: value_store)
    times = iter([1_000_000.0, 1_000_010.0])
    monkeypatch.setattr(time, "time", lambda: next(times))

    params = {"core_util_time_total": (0.0, 5.0, 10.0)}

    # First call only registers that the core is over the threshold.
    list(
        check_cpu_utilization_os(
            params, SectionCpuUtilizationOs(time_base=1e9, num_cpus=4, time_cpu=1.0)
        )
    )

    # time_base jumps by billions (simulating nanosecond ticks) while only
    # 10 seconds of real time actually pass (per the mocked time.time() calls).
    results = list(
        check_cpu_utilization_os(
            params, SectionCpuUtilizationOs(time_base=5e18, num_cpus=4, time_cpu=2.0)
        )
    )
    assert (
        Result(
            state=State.CRIT,
            summary="total is under high load for: 10 seconds (warn/crit at 5 seconds/10 seconds)",
        )
        in results
    )


def test_check_cpu_utilization_os_migrates_stale_high_load_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A "core is under high load since" timestamp written before this plugin
    # switched this_time to wall-clock time can be *smaller* than the new
    # time.time() too (e.g. cgroup v2's old this_time was uptime), so
    # this_time - stale_timestamp is a large *positive* number.
    # Such stale state must be discarded.
    value_store: dict[str, object] = {
        "util": (500_000.0, 100.0),
        "cpu.util.core.high": {"total": 500_000.0},
    }
    monkeypatch.setattr(cpu_utilization_os_plugin, "get_value_store", lambda: value_store)
    monkeypatch.setattr(time, "time", lambda: 1_800_000_000.0)

    params = {"core_util_time_total": (0.0, 5.0, 10.0)}
    results = list(
        check_cpu_utilization_os(
            params, SectionCpuUtilizationOs(time_base=500_010.0, num_cpus=4, time_cpu=110.0)
        )
    )

    assert not any(
        isinstance(r, Result) and r.summary.startswith("total is under high load") for r in results
    )
