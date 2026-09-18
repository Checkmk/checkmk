#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Sequence
from typing import Final
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import (
    FixedLevelsT,
    GetRateError,
    IgnoreResults,
    Metric,
    NoLevelsT,
    Result,
    State,
    StringTable,
)
from cmk.plugins.windows.agent_based import wmic_process

_NOW = 1628000000.0

_LEGEND = [
    "Name",
    "ThreadCount",
    "WorkingSetSize",
    "PageFileUsage",
    "UserModeTime",
    "KernelModeTime",
]

# "System Idle Process" reports two threads, so the CPU usage is relative to two cores.
_IDLE_PROCESS = ["System Idle Process", "2", "0", "0", "0", "0"]

_ONE_PROCESS = [
    _LEGEND,
    _IDLE_PROCESS,
    ["notepad.exe", "1", "536870912", "134217728", "600000000", "0"],
]

# The same totals spread over two processes, so only the count differs from _ONE_PROCESS.
_TWO_PROCESSES = [
    _LEGEND,
    _IDLE_PROCESS,
    ["notepad.exe", "1", "268435456", "67108864", "300000000", "0"],
    ["notepad.exe", "1", "268435456", "67108864", "300000000", "0"],
]

# Only the count matters here: three is a count the value store has no sample for.
_THREE_PROCESSES = [
    _LEGEND,
    _IDLE_PROCESS,
    ["notepad.exe", "1", "1", "1", "1", "0"],
    ["notepad.exe", "1", "1", "1", "1", "0"],
    ["notepad.exe", "1", "1", "1", "1", "0"],
]

type _Levels = NoLevelsT | FixedLevelsT[float]

_NO_LEVELS: Final[NoLevelsT] = ("no_levels", None)


def _params(
    *,
    name: str,
    mem_levels: _Levels,
    page_levels: _Levels,
    cpu_levels: _Levels,
) -> wmic_process.Params:
    return wmic_process.Params(
        name=name, mem_levels=mem_levels, page_levels=page_levels, cpu_levels=cpu_levels
    )


def _params_no_levels(name: str) -> wmic_process.Params:
    return _params(
        name=name,
        mem_levels=_NO_LEVELS,
        page_levels=_NO_LEVELS,
        cpu_levels=_NO_LEVELS,
    )


def _params_with_fixed_levels(name: str) -> wmic_process.Params:
    return _params(
        name=name,
        mem_levels=("fixed", (100.0, 200.0)),
        page_levels=("fixed", (50.0, 100.0)),
        cpu_levels=("fixed", (80.0, 90.0)),
    )


@pytest.fixture(name="seeded_value_store")
def fixture_seeded_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend the previous run was a minute ago, so `get_rate` yields a rate.

    The keys carry the process count, so seed every count a test reads a rate for.
    """
    store: dict[str, object] = {
        f"wmic_process.{counter}.notepad.exe.{count}": (_NOW - 60.0, 0.0)
        for counter in ("user", "kernel")
        for count in (1, 2)
    }
    monkeypatch.setattr(wmic_process, "get_value_store", lambda: store)


def _consume(
    params: wmic_process.Params, section: StringTable
) -> Sequence[IgnoreResults | Metric | Result]:
    with time_machine.travel(datetime.datetime.fromtimestamp(_NOW, tz=ZoneInfo("UTC"))):
        return list(wmic_process.check_wmic_process("notepad", params, section))


def _check(params: wmic_process.Params, section: StringTable) -> list[tuple[State, str]]:
    return [(r.state, r.summary) for r in _consume(params, section) if isinstance(r, Result)]


def _metrics(params: wmic_process.Params, section: StringTable) -> list[Metric]:
    return [m for m in _consume(params, section) if isinstance(m, Metric)]


@pytest.mark.usefixtures("seeded_value_store")
def test_fixed_levels_are_applied() -> None:
    reported = _check(_params_with_fixed_levels("notepad.exe"), _ONE_PROCESS)

    assert reported == [
        (State.OK, "Processes: 1"),
        (State.OK, "CPU: 50.00%"),
        (State.CRIT, "RAM: 512.0 MB (warn/crit at 100.0 MB/200.0 MB)"),
        (State.CRIT, "Page file: 128.0 MB (warn/crit at 50.0 MB/100.0 MB)"),
    ]


@pytest.mark.usefixtures("seeded_value_store")
def test_the_metrics_are_the_ones_of_the_legacy_check() -> None:
    """Existing RRDs are keyed on these names and hold MB rather than bytes.

    Preserving them is why this plug-in still renders memory in MB, so pin the whole
    set: the summaries the other tests compare never mention a metric name.
    """
    metrics = _metrics(_params_with_fixed_levels("notepad.exe"), _ONE_PROCESS)

    assert [(m.name, m.value, m.levels, m.boundaries) for m in metrics] == [
        ("user", 50.0, (80.0, 90.0), (0.0, 100.0)),
        ("kernel", 0.0, (80.0, 90.0), (0.0, 100.0)),
        ("mem", 512.0, (100.0, 200.0), (None, None)),
        ("page", 128.0, (50.0, 100.0), (None, None)),
    ]


@pytest.mark.usefixtures("seeded_value_store")
def test_absent_levels_keep_the_service_ok() -> None:
    reported = _check(_params_no_levels("notepad.exe"), _ONE_PROCESS)

    assert reported == [
        (State.OK, "Processes: 1"),
        (State.OK, "CPU: 50.00%"),
        (State.OK, "RAM: 512.0 MB"),
        (State.OK, "Page file: 128.0 MB"),
    ]


@pytest.mark.usefixtures("seeded_value_store")
def test_the_totals_are_summed_over_all_matching_processes() -> None:
    """Two processes holding half the totals each read like the single one."""
    reported = _check(_params_no_levels("notepad.exe"), _TWO_PROCESSES)

    assert reported == [
        (State.OK, "Processes: 2"),
        (State.OK, "CPU: 50.00%"),
        (State.OK, "RAM: 512.0 MB"),
        (State.OK, "Page file: 128.0 MB"),
    ]


@pytest.mark.usefixtures("seeded_value_store")
def test_an_unseen_process_count_restarts_the_cpu_rate() -> None:
    """A joining process brings its accumulated ticks along, which is not a rate.

    Keying the counters on the count, as the legacy check did, restarts the rate
    instead of reporting that jump.
    """
    with pytest.raises(GetRateError):
        _check(_params_no_levels("notepad.exe"), _THREE_PROCESSES)


def test_a_missing_process_name_is_reported() -> None:
    """The name is optional in the rule spec, so the enforced service may carry none.

    It cannot be required there: `check_default_parameters` is validated against the
    same form spec, and there is no process name that would be a sensible default.
    """
    params = wmic_process.Params(
        mem_levels=_NO_LEVELS, page_levels=_NO_LEVELS, cpu_levels=_NO_LEVELS
    )

    assert _check(params, _ONE_PROCESS) == [(State.UNKNOWN, "No process name configured")]


def test_an_empty_process_name_is_reported() -> None:
    """The form spec rejects an empty name, but rules.mk is not revalidated on load."""
    reported = _check(_params_no_levels(""), _ONE_PROCESS)

    assert reported == [(State.UNKNOWN, "No process name configured")]


def test_an_empty_section_names_the_agent_plugin() -> None:
    """The section is present but holds no lines, so the check is called with `[]`.

    Yielding nothing would let the engine report "Item not found in monitoring data",
    which is misleading: this plug-in is enforced only and never discovers an item.
    """
    reported = _check(_params_no_levels("notepad.exe"), [])

    assert reported == [(State.UNKNOWN, "No output from agent in section wmic_process")]
