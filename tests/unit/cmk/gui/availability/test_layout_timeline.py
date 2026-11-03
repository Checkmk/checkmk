#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Literal

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.availability.layout import layout_timeline
from cmk.gui.availability.options import get_default_avoptions
from cmk.gui.availability.type_defs import (
    AVLayoutTimeline,
    AVOptions,
    AVSpan,
    AVTimelineRow,
    AVTimelineStateName,
    AVTimelineStyle,
)


def _span(start: int, end: int) -> AVSpan:
    return {
        "site": SiteId("mysite"),
        "host_name": HostName("myhost"),
        "service_description": "Process nginx",
        "from": start,
        "until": end,
        "duration": end - start,
        "state": 0,
        "host_down": 0,
        "in_downtime": 0,
        "in_host_downtime": 0,
        "in_notification_period": 1,
        "in_service_period": 1,
        "is_flapping": 0,
    }


def _row(start: int, end: int, state: AVTimelineStateName = "ok") -> AVTimelineRow:
    return _span(start, end), state


def _row_with_output(output: str) -> AVTimelineRow:
    span = _span(0, 100)
    span["log_output"] = output
    return span, "ok"


def _avoptions(
    until: float = 100.0, service_period: Literal["honor", "ignore"] = "honor"
) -> AVOptions:
    avoptions = get_default_avoptions((0.0, until))
    avoptions["dateformat"] = "epoch"
    avoptions["service_period"] = service_period
    return avoptions


def _layout(
    rows: list[AVTimelineRow],
    style: AVTimelineStyle = "standalone",
    avoptions: AVOptions | None = None,
) -> AVLayoutTimeline:
    return layout_timeline("service", rows, 100, avoptions or _avoptions(), style)


def test_an_unmonitored_span_is_rendered_unmonitored() -> None:
    [(_row_nr, _title, _width, css)] = _layout([_row(0, 100, "unmonitored")])["spans"]
    assert css == "unmonitored"


def test_a_span_title_names_its_period() -> None:
    [(_nr, title, _width, _css)] = _layout([_row(0, 100)])["spans"]
    assert title.startswith("From 0 until 100 ")


def test_a_span_title_ends_with_the_state_and_its_log_output() -> None:
    [(_nr, title, _width, _css)] = _layout([_row_with_output("all fine")])["spans"]
    assert title.endswith(" OK - all fine")


def test_a_detail_row_carries_the_state() -> None:
    [row] = _layout([_row(0, 100)])["table"]
    assert (row["css"], row["state_name"]) == ("state0", "OK")


def test_a_detail_row_carries_its_period() -> None:
    [row] = _layout([_row(0, 100)])["table"]
    assert (row["from_text"], row["until_text"]) == ("0", "100")


def _local_time(day: int, hour: int) -> int:
    return int(time.mktime((2024, 5, day, hour, 0, 0, 0, 0, -1)))


def _from_text_for_range(start: int, end: int) -> str:
    avoptions = get_default_avoptions((float(start), float(end)))
    avoptions["dateformat"] = "yyyy-mm-dd hh:mm:ss"
    [row] = layout_timeline("service", [_row(start, end)], end - start, avoptions, "standalone")[
        "table"
    ]
    return row["from_text"]


def test_a_range_within_one_day_renders_only_the_time() -> None:
    assert _from_text_for_range(_local_time(6, 10), _local_time(6, 11)) == "10:00:00"


def test_a_range_over_several_days_renders_the_date_too() -> None:
    assert _from_text_for_range(_local_time(6, 10), _local_time(8, 10)) == "2024-05-06 10:00:00"


def test_a_detail_row_carries_the_log_output() -> None:
    [row] = _layout([_row_with_output("all fine")])["table"]
    assert row.get("log_output") == "all fine"


def test_a_gap_before_a_span_is_shown_as_untitled_unmonitored_span() -> None:
    spans = _layout([_row(20, 100)])["spans"]
    assert spans[0] == (None, "", 20.0, "unmonitored")


def test_a_gap_after_the_last_span_is_filled_when_honoring_the_service_period() -> None:
    spans = _layout([_row(0, 80)], avoptions=_avoptions(service_period="honor"))["spans"]
    assert spans[-1] == (None, "", 20.0, "unmonitored")


def test_a_gap_after_the_last_span_is_left_empty_when_ignoring_the_service_period() -> None:
    spans = _layout([_row(0, 80)], avoptions=_avoptions(service_period="ignore"))["spans"]
    assert [css for _nr, _title, _width, css in spans] == ["state0"]


def test_a_short_span_is_widened_so_it_stays_visible() -> None:
    spans = _layout([_row(0, 99), _row(99, 100, "crit")])["spans"]
    assert spans[1][2] == pytest.approx(0.99 + 0.5)


def test_inline_does_not_widen_a_short_span() -> None:
    spans = _layout([_row(0, 99), _row(99, 100, "crit")], style="inline")["spans"]
    assert spans[1][2] == pytest.approx(1.0)


def test_an_inline_timeline_with_many_state_changes_fills_the_bar() -> None:
    rows = [_row(n, n + 1, "crit" if n % 2 else "ok") for n in range(200)]
    timeline = _layout(rows, "inline", _avoptions(until=200.0))
    assert sum(width for _nr, _title, width, _css in timeline["spans"]) == pytest.approx(100.0)


def test_inline_collapses_four_tiny_spans_into_one_chaos_span() -> None:
    tiny = [_row(n, n + 1, "crit" if n % 2 else "ok") for n in range(4)]
    timeline = _layout([*tiny, _row(4, 10000)], "inline", _avoptions(until=10000.0))
    assert [css for _nr, _title, _width, css in timeline["spans"]] == ["chaos", "state0"]


def test_a_chaos_span_starts_with_its_first_tiny_span() -> None:
    tiny = [_row(n, n + 1, "crit" if n % 2 else "ok") for n in range(4)]
    [chaos, _ok] = _layout([*tiny, _row(4, 10000)], "inline", _avoptions(until=10000.0))["spans"]
    assert chaos[1].startswith("4 chaotic state changes from 0 until 4 ")


def test_fewer_than_four_tiny_spans_at_the_end_are_no_chaos_span() -> None:
    rows = [_row(0, 9998), _row(9998, 9999, "crit"), _row(9999, 10000)]
    timeline = _layout(rows, "inline", _avoptions(until=10000.0))
    assert [css for _nr, _title, _width, css in timeline["spans"]] == ["state0"]


def test_a_chaos_span_at_the_end_comes_before_the_trailing_gap() -> None:
    tiny = [_row(n, n + 1, "crit" if n % 2 else "ok") for n in range(9990, 9994)]
    timeline = _layout([_row(0, 9990), *tiny], "inline", _avoptions(until=10000.0))
    assert [css for _nr, _title, _width, css in timeline["spans"]] == [
        "state0",
        "chaos",
        "unmonitored",
    ]


def test_a_chaos_span_before_a_gap_comes_before_the_gap() -> None:
    tiny = [_row(n, n + 1, "crit" if n % 2 else "ok") for n in range(4)]
    timeline = _layout([*tiny, _row(5000, 10000)], "inline", _avoptions(until=10000.0))
    assert [css for _nr, _title, _width, css in timeline["spans"]] == [
        "chaos",
        "unmonitored",
        "state0",
    ]


def _ps_row(long_output: str, check_command: str, escape_plugin_output: str) -> AVTimelineRow:
    span = _span(0, 100)
    span["long_log_output"] = long_output
    span["service_check_command"] = check_command
    span["service_custom_variables"] = {"ESCAPE_PLUGIN_OUTPUT": escape_plugin_output}
    return span, "ok"


def _long_output(row: AVTimelineRow) -> str:
    [table_row] = _layout([row])["table"]
    return table_row.get("long_log_output", "")


def test_unescaped_ps_long_output_gets_its_backslashes_back() -> None:
    # Werk 16701: ps encodes backslashes as "&bsol%3B" when plugin output is not escaped
    # (werk 15523); the availability table has to turn them back into backslashes.
    row = _ps_row("<td>D:&bsol%3Bnginx.exe</td>", "check_mk-ps", "0")
    assert _long_output(row) == "<td>D:\\nginx.exe</td>"


def test_escaped_ps_long_output_is_kept_as_it_is() -> None:
    row = _ps_row("<td>D:&bsol%3Bnginx.exe</td>", "check_mk-ps", "1")
    assert _long_output(row) == "<td>D:&bsol%3Bnginx.exe</td>"


def test_long_output_of_other_checks_is_kept_as_it_is() -> None:
    row = _ps_row("<td>D:&bsol%3Bnginx.exe</td>", "check_mk-cpu_loads", "0")
    assert _long_output(row) == "<td>D:&bsol%3Bnginx.exe</td>"


def test_inline_timelines_have_no_detail_table() -> None:
    assert _layout([_row(0, 100)], style="inline")["table"] == []
