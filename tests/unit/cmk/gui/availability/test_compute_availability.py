#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.availability.computation import (
    compute_availability,
    melt_short_intervals,
    merge_timeline,
)
from cmk.gui.availability.options import get_default_avoptions
from cmk.gui.availability.type_defs import (
    AVEntry,
    AVObjectType,
    AVOutageStatistics,
    AVSpan,
    AVTimelineRow,
)

_OK = 0
_CRIT = 2


def _span(
    start: int,
    end: int,
    state: int = _OK,
    *,
    host_groups: list[str] | None = None,
    service_groups: list[str] | None = None,
) -> AVSpan:
    span: AVSpan = {
        "site": SiteId("heute"),
        "host_name": HostName("heute"),
        "service_description": "CPU load",
        "from": start,
        "until": end,
        "duration": end - start,
        "state": state,
        "host_down": 0,
        "in_downtime": 0,
        "in_host_downtime": 0,
        "in_notification_period": 1,
        "in_service_period": 1,
        "is_flapping": 0,
    }
    if host_groups is not None:
        span["host_groups"] = host_groups
    if service_groups is not None:
        span["service_groups"] = service_groups
    return span


def _row(start: int, end: int, state: str) -> AVTimelineRow:
    return _span(start, end), state


def _compute(
    spans: list[AVSpan],
    *,
    what: AVObjectType = "service",
    grouping: Literal["host", "host_groups", "service_groups"] | None = None,
    dont_merge: bool = False,
    short_intervals: int = 0,
    outage_statistics: AVOutageStatistics | None = None,
) -> AVEntry:
    avoptions = get_default_avoptions((0.0, 1000.0))
    avoptions["grouping"] = grouping
    avoptions["dont_merge"] = dont_merge
    avoptions["short_intervals"] = short_intervals
    avoptions["outage_statistics"] = outage_statistics or ([], [])
    [entry] = compute_availability(
        what, {(SiteId("heute"), HostName("heute")): {"CPU load": spans}}, avoptions, {}
    )
    return entry


def test_host_groups_of_all_spans_are_collected() -> None:
    entry = _compute(
        [_span(0, 10, host_groups=["linux"]), _span(10, 20, host_groups=["web"])],
        grouping="host_groups",
    )
    assert entry["groups"] == {"linux", "web"}


def test_service_groups_of_all_spans_are_collected() -> None:
    entry = _compute(
        [_span(0, 10, service_groups=["cpu"]), _span(10, 20, service_groups=["load"])],
        grouping="service_groups",
    )
    assert entry["groups"] == {"cpu", "load"}


def test_bi_does_not_collect_groups_from_spans() -> None:
    entry = _compute([_span(0, 10, host_groups=["linux"])], what="bi", grouping="host_groups")
    assert entry["groups"] == set()


def test_outage_statistics_count_the_shortest_and_longest_span() -> None:
    # Longest first, shortest in the middle: neither extreme sits where a
    # keep-first or take-last accumulator would pick it up by accident.
    entry = _compute(
        [
            _span(0, 30, _CRIT),
            _span(30, 40),
            _span(40, 50, _CRIT),
            _span(50, 60),
            _span(60, 80, _CRIT),
        ],
        outage_statistics=(["min", "max", "cnt"], ["crit"]),
    )
    assert entry["statistics"]["crit"] == (3, 10, 30)


def test_without_outage_statistics_nothing_is_counted() -> None:
    entry = _compute([_span(0, 10, _CRIT), _span(10, 50), _span(50, 80, _CRIT)])
    assert not entry["statistics"]


def test_adjacent_spans_of_the_same_state_are_merged() -> None:
    entry = _compute([_span(0, 10), _span(10, 20)])
    assert len(entry["timeline"]) == 1


def test_dont_merge_keeps_adjacent_spans_of_the_same_state_apart() -> None:
    entry = _compute([_span(0, 10), _span(10, 20)], dont_merge=True)
    assert len(entry["timeline"]) == 2


def test_without_short_intervals_a_short_outage_is_counted() -> None:
    entry = _compute([_span(0, 100), _span(100, 102, _CRIT), _span(102, 200)])
    assert entry["states"]["crit"] == 2


def test_short_intervals_melt_a_short_outage_into_its_surroundings() -> None:
    entry = _compute([_span(0, 100), _span(100, 102, _CRIT), _span(102, 200)], short_intervals=5)
    assert "crit" not in entry["states"]


def test_merge_timeline_joins_adjacent_rows_of_the_same_state() -> None:
    rows = [_row(0, 10, "ok"), _row(10, 30, "ok")]
    merge_timeline(rows)
    [(span, _state)] = rows
    assert (span["until"], span["duration"]) == (30, 30)


def test_merge_timeline_keeps_rows_with_a_gap_apart() -> None:
    rows = [_row(0, 10, "ok"), _row(20, 30, "ok")]
    merge_timeline(rows)
    assert len(rows) == 2


def test_merge_timeline_keeps_rows_of_different_states_apart() -> None:
    rows = [_row(0, 10, "ok"), _row(10, 30, "crit")]
    merge_timeline(rows)
    assert len(rows) == 2


def test_a_short_row_between_equal_neighbours_takes_their_state_in_place() -> None:
    rows = [_row(0, 100, "ok"), _row(100, 105, "crit"), _row(105, 200, "ok")]
    melt_short_intervals(rows, 5, dont_merge=True)
    assert rows[1][1] == "ok"


def test_a_short_row_between_different_neighbours_keeps_its_state() -> None:
    rows = [_row(0, 100, "ok"), _row(100, 102, "crit"), _row(102, 200, "warn")]
    melt_short_intervals(rows, 5, dont_merge=True)
    assert rows[1][1] == "crit"


def test_a_row_longer_than_the_threshold_keeps_its_state() -> None:
    rows = [_row(0, 100, "ok"), _row(100, 110, "crit"), _row(110, 200, "ok")]
    melt_short_intervals(rows, 5, dont_merge=True)
    assert rows[1][1] == "crit"


def test_the_first_row_is_never_melted() -> None:
    rows = [_row(0, 2, "crit"), _row(2, 100, "ok"), _row(100, 200, "ok")]
    melt_short_intervals(rows, 5, dont_merge=True)
    assert rows[0][1] == "crit"


def test_the_last_row_is_never_melted() -> None:
    rows = [_row(0, 100, "ok"), _row(100, 198, "ok"), _row(198, 200, "crit")]
    melt_short_intervals(rows, 5, dont_merge=True)
    assert rows[2][1] == "crit"


def _ok_crit_warn_crit_ok() -> list[AVTimelineRow]:
    return [
        _row(0, 100, "ok"),
        _row(100, 102, "crit"),
        _row(102, 104, "warn"),
        _row(104, 106, "crit"),
        _row(106, 200, "ok"),
    ]


def test_a_row_that_becomes_short_and_enclosed_after_merging_is_melted_too() -> None:
    # Only warn is enclosed at first; the crit row it merges into is melted on re-entry.
    rows = _ok_crit_warn_crit_ok()
    melt_short_intervals(rows, 10, dont_merge=False)
    assert [state for _, state in rows] == ["ok"]


def test_dont_merge_stops_melting_after_the_first_pass() -> None:
    rows = _ok_crit_warn_crit_ok()
    melt_short_intervals(rows, 10, dont_merge=True)
    assert [state for _, state in rows] == ["ok", "crit", "crit", "crit", "ok"]
