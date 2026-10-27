#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from urllib.parse import parse_qs, urlsplit

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.availability.layout import layout_availability_table
from cmk.gui.availability.options import get_default_avoptions
from cmk.gui.availability.type_defs import (
    AVData,
    AVEntry,
    AVLayoutTable,
    AVObjectType,
    AVOptions,
    AVOutageStatisticsAggregations,
    AVTimelineStates,
    AVTimelineStatistics,
)
from cmk.web.utils.urls import HTTPVariable

_STATISTICS: AVOutageStatisticsAggregations = ["min", "max", "avg", "cnt"]


def _entry(
    states: AVTimelineStates,
    statistics: AVTimelineStatistics | None = None,
    service: str = "CPU load",
) -> AVEntry:
    return {
        "site": SiteId("mysite"),
        "host": HostName("myhost"),
        "alias": "My host",
        "service": service,
        "display_name": "Load",
        "states": states,
        "considered_duration": 100,
        "total_duration": 100,
        "statistics": statistics or {},
        "groups": None,
        "timeline": [],
    }


def _avoptions() -> AVOptions:
    avoptions = get_default_avoptions((0.0, 100.0))
    avoptions["timeformat"] = ("time", None, "seconds")
    avoptions["av_levels"] = None
    return avoptions


def _make_uri(addvars: Sequence[HTTPVariable]) -> str:
    return "|".join(f"{var}={value}" for var, value in addvars)


def _layout(
    av_data: AVData, avoptions: AVOptions | None = None, what: AVObjectType = "service"
) -> AVLayoutTable:
    return layout_availability_table(what, None, av_data, avoptions or _avoptions(), _make_uri)


def _cell(av_table: AVLayoutTable, title: str, row: int = 0) -> tuple[str, str]:
    titles = [cell_title for cell_title, _help in av_table["cell_titles"]]
    text, css = av_table["rows"][row]["cells"][titles.index(title)]
    return str(text), str(css)


def _summary_cell(av_table: AVLayoutTable, title: str) -> tuple[str, str]:
    titles = [cell_title for cell_title, _help in av_table["cell_titles"]]
    text, css = av_table["summary"][titles.index(title)]
    return str(text), str(css)


def test_service_object_cells_link_to_host_and_service() -> None:
    [row] = _layout([_entry({"ok": 100})])["rows"]
    assert [(name, parse_qs(urlsplit(url).query)) for name, url in row["object"]] == [
        ("myhost", {"view_name": ["hoststatus"], "site": ["mysite"], "host": ["myhost"]}),
        (
            "CPU load",
            {
                "view_name": ["service"],
                "site": ["mysite"],
                "host": ["myhost"],
                "service": ["CPU load"],
            },
        ),
    ]


def test_use_display_name_labels_the_service_with_its_display_name() -> None:
    avoptions = _avoptions()
    avoptions["labelling"] = ["use_display_name"]
    [row] = _layout([_entry({"ok": 100})], avoptions)["rows"]
    assert [name for name, _url in row["object"]] == ["myhost", "Load"]


def test_bi_object_cell_is_the_aggregate() -> None:
    [row] = _layout([_entry({"ok": 100}, service="My aggregate")], what="bi")["rows"]
    assert [name for name, _url in row["object"]] == ["My aggregate"]


def test_service_row_links_to_its_timeline_and_history() -> None:
    [row] = _layout([_entry({"ok": 100})])["rows"]
    assert [icon for icon, _title, _url in row["urls"]] == ["timeline", "history"]


def test_timeline_url_selects_the_service() -> None:
    [row] = _layout([_entry({"ok": 100})])["rows"]
    _icon, _title, url = row["urls"][0]
    assert url == "av_mode=timeline|av_site=mysite|av_host=myhost|av_service=CPU load"


def test_bi_row_links_only_to_the_aggregate_timeline() -> None:
    [row] = _layout([_entry({"ok": 100}, service="My aggregate")], what="bi")["rows"]
    assert row["urls"] == [
        (
            "timeline",
            "Timeline",
            "av_mode=timeline|av_aggr_group=myhost|aggr_name=My aggregate|view_name=aggr_single",
        )
    ]


def test_omit_buttons_drops_the_urls() -> None:
    avoptions = _avoptions()
    avoptions["labelling"] = ["omit_buttons"]
    [row] = _layout([_entry({"ok": 100})], avoptions)["rows"]
    assert row["urls"] == []


def test_a_state_that_never_occurred_is_rendered_unused() -> None:
    assert _cell(_layout([_entry({"ok": 100})]), "CRIT")[1].startswith("unused ")


def test_without_av_levels_ok_keeps_its_own_color() -> None:
    assert _cell(_layout([_entry({"ok": 90, "crit": 10})]), "OK")[1].startswith("state0 ")


def test_ok_below_the_crit_level_is_rendered_critical() -> None:
    avoptions = _avoptions()
    avoptions["av_levels"] = (99.0, 95.0)
    av_table = _layout([_entry({"ok": 90, "crit": 10})], avoptions)
    assert _cell(av_table, "OK")[1].startswith("state2 ")


def test_ok_between_the_levels_is_rendered_warning() -> None:
    avoptions = _avoptions()
    avoptions["av_levels"] = (99.0, 95.0)
    av_table = _layout([_entry({"ok": 97, "crit": 3})], avoptions)
    assert _cell(av_table, "OK")[1].startswith("state1 ")


def _two_rows() -> AVData:
    return [_entry({"ok": 60, "crit": 40}), _entry({"ok": 80, "crit": 20})]


def _two_rows_and_an_unmonitored_one() -> AVData:
    return [*_two_rows(), _entry({})]


def test_sum_summary_adds_up_the_times() -> None:
    avoptions = _avoptions()
    avoptions["summary"] = "sum"
    assert _summary_cell(_layout(_two_rows(), avoptions), "OK")[0] == "140 s"


def test_average_summary_divides_by_the_monitored_rows() -> None:
    avoptions = _avoptions()
    avoptions["summary"] = "average"
    assert _summary_cell(_layout(_two_rows_and_an_unmonitored_one(), avoptions), "OK")[0] == "70 s"


def test_percentage_summary_is_the_average_even_when_summing() -> None:
    avoptions = _avoptions()
    avoptions["summary"] = "sum"
    avoptions["timeformat"] = ("perc", "percentage_0", None)
    assert _summary_cell(_layout(_two_rows_and_an_unmonitored_one(), avoptions), "OK")[0] == "70%"


def test_summary_levels_use_the_average_percentage_even_when_summing_times() -> None:
    avoptions = _avoptions()
    avoptions["summary"] = "sum"
    avoptions["av_levels"] = (99.0, 95.0)
    assert _summary_cell(_layout(_two_rows(), avoptions), "OK")[1].startswith("state2 ")


def test_without_summary_option_there_is_no_summary() -> None:
    avoptions = _avoptions()
    avoptions["summary"] = None
    assert "summary" not in _layout([_entry({"ok": 100})], avoptions)


def _with_crit_statistics() -> AVOptions:
    avoptions = _avoptions()
    avoptions["outage_statistics"] = (_STATISTICS, ["crit"])
    return avoptions


def test_outage_statistics_add_columns_after_their_state() -> None:
    titles = [title for title, _help in _layout([], _with_crit_statistics())["cell_titles"]]
    crit = titles.index("CRIT")
    assert titles[crit + 1 : crit + 5] == ["Shortest", "Longest", "Average", "Count"]


def test_outage_statistics_show_shortest_longest_average_and_count() -> None:
    entry = _entry({"ok": 70, "crit": 30}, statistics={"crit": (3, 5, 15)})
    av_table = _layout([entry], _with_crit_statistics())
    assert [_cell(av_table, title)[0] for title in ["Shortest", "Longest", "Average", "Count"]] == [
        "5 s",
        "15 s",
        "10 s",
        "3",
    ]


def test_outage_statistics_are_empty_for_a_row_without_statistics() -> None:
    av_table = _layout([_entry({"ok": 70, "crit": 30})], _with_crit_statistics())
    assert _cell(av_table, "Count") == ("", "")


def _rows_with_crit_counts() -> AVData:
    return [
        _entry({"ok": 70, "crit": 30}, statistics={"crit": (3, 5, 15)}),
        _entry({"ok": 90, "crit": 10}, statistics={"crit": (1, 10, 10)}),
    ]


def test_sum_summary_adds_up_the_outage_counts() -> None:
    avoptions = _with_crit_statistics()
    avoptions["summary"] = "sum"
    assert _summary_cell(_layout(_rows_with_crit_counts(), avoptions), "Count")[0] == "4"


def test_average_summary_averages_the_outage_counts() -> None:
    avoptions = _with_crit_statistics()
    avoptions["summary"] = "average"
    assert _summary_cell(_layout(_rows_with_crit_counts(), avoptions), "Count")[0] == "2.00"
