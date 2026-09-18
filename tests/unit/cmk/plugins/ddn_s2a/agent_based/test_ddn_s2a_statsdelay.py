#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.ddn_s2a.agent_based import ddn_s2a_statsdelay
from cmk.plugins.ddn_s2a.agent_based.ddn_s2a_statsdelay import (
    check_ddn_s2a_statsdelay,
    discover_ddn_s2a_statsdelay,
    parse_ddn_s2a_statsdelay,
)

# Three delay bins; the ">10.0" bin is reported as 30 seconds.
_RESPONSE = (
    "0@30@time_interval_in_seconds@0.1@host_reads@10@host_writes@20"
    "@disk_reads@5@disk_writes@6"
    "@time_interval_in_seconds@0.2@host_reads@30@host_writes@40"
    "@disk_reads@7@disk_writes@8"
    "@time_interval_in_seconds@>10.0@host_reads@50@host_writes@60"
    "@disk_reads@9@disk_writes@10@$"
)

_SECTION = parse_ddn_s2a_statsdelay([[_RESPONSE]])

_PARAMS = {"read_avg": (0.1, 0.2), "write_avg": (0.1, 0.2)}


def test_parse_ddn_s2a_statsdelay() -> None:
    assert _SECTION.time_intervals == [0.1, 0.2, 30.0]
    assert _SECTION.disk_reads == [5, 7, 9]


def test_discover_ddn_s2a_statsdelay() -> None:
    assert list(discover_ddn_s2a_statsdelay(_SECTION)) == [
        Service(item="Disk"),
        Service(item="Host"),
    ]


def test_check_ddn_s2a_statsdelay(monkeypatch: pytest.MonkeyPatch) -> None:
    # One read landed in the 0.2s bin and two writes in the 30s bin since the last check.
    _set_value_store(
        monkeypatch, {"time_intervals": [0.1, 0.2, 30.0], "reads": [5, 6, 9], "writes": [6, 8, 8]}
    )

    assert list(check_ddn_s2a_statsdelay("Disk", _PARAMS, _SECTION)) == [
        Result(state=State.CRIT, summary="Average read wait: 0.20 s (warn/crit at 0.10/0.20 s)"),
        Metric("disk_average_read_wait", 0.2, levels=(0.1, 0.2)),
        Result(state=State.OK, summary="Min. read wait: 0.20 s"),
        Metric("disk_min_read_wait", 0.2),
        Result(state=State.OK, summary="Max. read wait: 0.20 s"),
        Metric("disk_max_read_wait", 0.2),
        Result(state=State.CRIT, summary="Average write wait: 30.00 s (warn/crit at 0.10/0.20 s)"),
        Metric("disk_average_write_wait", 30.0, levels=(0.1, 0.2)),
        Result(state=State.OK, summary="Min. write wait: 30.00 s"),
        Metric("disk_min_write_wait", 30.0),
        Result(state=State.OK, summary="Max. write wait: 30.00 s"),
        Metric("disk_max_write_wait", 30.0),
    ]


def test_check_ddn_s2a_statsdelay_initializes(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _set_value_store(monkeypatch, {})

    with pytest.raises(IgnoreResultsError, match="Initializing"):
        list(check_ddn_s2a_statsdelay("Host", _PARAMS, _SECTION))

    assert store["reads"] == [10, 30, 50]


def test_check_ddn_s2a_statsdelay_reinitializes_on_new_bins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_value_store(monkeypatch, {"time_intervals": [0.1, 0.2], "reads": [0, 0], "writes": [0, 0]})

    with pytest.raises(IgnoreResultsError, match="Time intervals have changed"):
        list(check_ddn_s2a_statsdelay("Host", _PARAMS, _SECTION))


def test_check_ddn_s2a_statsdelay_without_traffic(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_value_store(
        monkeypatch,
        {"time_intervals": [0.1, 0.2, 30.0], "reads": [10, 30, 50], "writes": [20, 40, 60]},
    )

    with pytest.raises(IgnoreResultsError, match="No writes or reads since last check"):
        list(check_ddn_s2a_statsdelay("Host", _PARAMS, _SECTION))


def _set_value_store(
    monkeypatch: pytest.MonkeyPatch, store: dict[str, object]
) -> dict[str, object]:
    monkeypatch.setattr(ddn_s2a_statsdelay, "get_value_store", lambda: store)
    return store
