#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.availability.computation import (
    cell_active,
    check_av_levels,
    compute_availability_groups,
    pass_availability_filter,
)
from cmk.gui.availability.options import get_default_avoptions
from cmk.gui.availability.type_defs import (
    AVEntry,
    AVGroupIds,
    AVOptions,
    AVTimelineStates,
)

_LEVELS = (99.0, 95.0)


def _entry(
    host: str = "myhost",
    groups: AVGroupIds = None,
    states: AVTimelineStates | None = None,
    considered_duration: int = 100,
) -> AVEntry:
    return {
        "site": SiteId("mysite"),
        "host": HostName(host),
        "alias": host,
        "service": "CPU load",
        "display_name": "CPU load",
        "states": states or {},
        "considered_duration": considered_duration,
        "total_duration": considered_duration,
        "statistics": {},
        "groups": groups,
        "timeline": [],
    }


def _avoptions(
    grouping: Literal["host", "host_groups", "service_groups"] | None = None,
) -> AVOptions:
    avoptions = get_default_avoptions((0.0, 100.0))
    avoptions["grouping"] = grouping
    return avoptions


def _tables_by_title(av_data: list[AVEntry], group_titles: dict[str, str]) -> dict[str, list[str]]:
    return {
        str(title): [str(entry["host"]) for entry in table]
        for title, table in compute_availability_groups(
            "service", av_data, _avoptions("host_groups"), group_titles
        )
    }


def test_without_grouping_all_rows_form_one_untitled_table() -> None:
    av_data = [_entry("a"), _entry("b")]
    assert compute_availability_groups("service", av_data, _avoptions(None), {}) == [
        (None, av_data)
    ]


def test_grouping_by_host_titles_the_group_with_the_host_name_only() -> None:
    entry = _entry("myhost", groups=[(SiteId("mysite"), HostName("myhost"))])
    [(title, _table)] = compute_availability_groups("service", [entry], _avoptions("host"), {})
    assert title == "myhost"


def test_a_group_is_titled_with_its_alias() -> None:
    tables = _tables_by_title([_entry(groups={"linux"})], {"linux": "Linux servers"})
    assert list(tables) == ["Linux servers"]


def test_a_group_without_alias_is_titled_with_its_name() -> None:
    tables = _tables_by_title([_entry(groups={"linux"})], {})
    assert list(tables) == ["linux"]


def test_ungrouped_rows_form_the_not_contained_table() -> None:
    tables = _tables_by_title([_entry("lonely", groups=set())], {})
    assert tables == {"Not contained in any group": ["lonely"]}


def test_a_grouped_row_is_not_in_the_not_contained_table() -> None:
    tables = _tables_by_title(
        [_entry("lonely", groups=set()), _entry("grouped", groups={"linux"})], {}
    )
    assert "grouped" not in tables["Not contained in any group"]


def test_a_row_is_not_in_the_table_of_a_group_it_is_not_in() -> None:
    tables = _tables_by_title(
        [_entry("linux_host", groups={"linux"}), _entry("web_host", groups={"web"})], {}
    )
    assert "web_host" not in tables["linux"]


def test_an_ungrouped_row_is_not_in_the_table_of_a_group() -> None:
    tables = _tables_by_title(
        [_entry("lonely", groups=set()), _entry("grouped", groups={"linux"})], {}
    )
    assert "lonely" not in tables["linux"]


def _passes(
    states: AVTimelineStates,
    *,
    warn: float = 0.0,
    crit: float = 0.0,
    non_ok: float = 0.0,
    considered_duration: int = 100,
) -> bool:
    avoptions = _avoptions()
    avoptions["av_filter_outages"] = {"warn": warn, "crit": crit, "non-ok": non_ok}
    return pass_availability_filter(
        _entry(states=states, considered_duration=considered_duration), avoptions
    )


def test_a_row_without_considered_duration_always_passes() -> None:
    assert _passes({}, crit=50.0, considered_duration=0)


def test_a_row_with_too_little_warn_is_filtered_out() -> None:
    assert not _passes({"ok": 90, "warn": 10}, warn=20.0)


def test_the_crit_level_counts_down_for_hosts() -> None:
    assert _passes({"up": 50, "down": 50}, crit=40.0)


def test_the_crit_level_filters_out_too_little_down() -> None:
    assert not _passes({"up": 50, "down": 50}, crit=60.0)


def test_non_ok_sums_the_outage_states() -> None:
    assert _passes({"ok": 80, "warn": 10, "crit": 10}, non_ok=20.0)


def test_non_ok_does_not_count_unmonitored() -> None:
    assert not _passes({"ok": 10, "unmonitored": 70, "warn": 10, "crit": 10}, non_ok=30.0)


def test_av_mode_hides_every_state_but_ok() -> None:
    avoptions = _avoptions()
    avoptions["av_mode"] = True
    assert (cell_active("ok", avoptions), cell_active("crit", avoptions)) == (True, False)


def test_out_of_notification_period_is_shown_only_when_honored() -> None:
    avoptions = _avoptions()
    avoptions["notification_period"] = "ignore"
    hidden = cell_active("outof_notification_period", avoptions)
    avoptions["notification_period"] = "honor"
    assert (hidden, cell_active("outof_notification_period", avoptions)) == (False, True)


def test_out_of_service_period_is_never_shown() -> None:
    avoptions = _avoptions()
    avoptions["service_period"] = "honor"
    assert not cell_active("outof_service_period", avoptions)


def test_in_downtime_is_shown_only_when_honored() -> None:
    avoptions = _avoptions()
    avoptions["downtimes"] = {"include": "ignore", "exclude_ok": False}
    hidden = cell_active("in_downtime", avoptions)
    avoptions["downtimes"] = {"include": "honor", "exclude_ok": False}
    assert (hidden, cell_active("in_downtime", avoptions)) == (False, True)


def test_unmonitored_is_shown_only_when_considered() -> None:
    avoptions = _avoptions()
    avoptions["consider"] = {"flapping": True, "host_down": True, "unmonitored": False}
    assert not cell_active("unmonitored", avoptions)


def test_flapping_is_shown_only_when_considered() -> None:
    avoptions = _avoptions()
    avoptions["consider"] = {"flapping": False, "host_down": True, "unmonitored": True}
    assert not cell_active("flapping", avoptions)


def test_host_down_is_shown_only_when_considered() -> None:
    avoptions = _avoptions()
    avoptions["consider"] = {"flapping": True, "host_down": False, "unmonitored": True}
    assert not cell_active("host_down", avoptions)


def test_a_state_grouped_into_another_state_is_hidden() -> None:
    avoptions = _avoptions()
    avoptions["state_grouping"] = {"warn": "crit", "unknown": "unknown", "host_down": "host_down"}
    assert not cell_active("warn", avoptions)


def test_a_state_grouped_into_itself_is_shown() -> None:
    avoptions = _avoptions()
    avoptions["state_grouping"] = {"warn": "warn", "unknown": "unknown", "host_down": "host_down"}
    assert cell_active("warn", avoptions)


def test_a_host_state_grouped_into_another_state_is_hidden() -> None:
    avoptions = _avoptions()
    avoptions["host_state_grouping"] = {"unreach": "down"}
    assert not cell_active("unreach", avoptions)


def test_no_levels_are_checked_without_considered_duration() -> None:
    assert check_av_levels(0, _LEVELS, 0) == 0


def test_availability_below_crit_is_critical() -> None:
    assert check_av_levels(90, _LEVELS, 100) == 2


def test_availability_exactly_at_crit_is_only_warning() -> None:
    assert check_av_levels(95, _LEVELS, 100) == 1


def test_availability_between_the_levels_is_warning() -> None:
    assert check_av_levels(97, _LEVELS, 100) == 1


def test_availability_at_warn_is_ok() -> None:
    assert check_av_levels(99, _LEVELS, 100) == 0
