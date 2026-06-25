#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the pure parsing/aggregation helpers in the Livestatus backend.

These cover the typed row accessors, the WATO folder-path parsing, the prepared
folder-skeleton conversion and the state/detail row builders — all without
opening a Livestatus socket. (The perf_data parser now lives in the shared
cmk.maps.shared.perfdata, and LQL value escaping is cmk.livestatus_client's
lqencode; see tests/unit/cmk/utils.)
"""

from __future__ import annotations

import pytest

from cmk.maps.backend.connections.livestatus import (
    _apply_extra,
    _build_details,
    _default_site_id,
    _folder_info_from_entry,
    _folder_path_from_filename,
    _parse_host_state_row,
    _parse_service_state_row,
    _services_summary_from_row,
    _worst_state_dict,
)
from cmk.maps.backend.schemas.state import ObjectState


def test_services_summary_maps_five_consecutive_columns() -> None:
    summary = _services_summary_from_row([99, 1, 2, 3, 4, 5], base=1)
    assert summary.ok == 1
    assert summary.warning == 2
    assert summary.critical == 3
    assert summary.unknown == 4
    assert summary.pending == 5


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        pytest.param("/wato/datacenters/muc/hosts.mk", "datacenters/muc", id="nested"),
        pytest.param("/wato/hosts.mk", "", id="root-with-leading-slash"),
        pytest.param("wato/hosts.mk", "", id="root-no-leading-slash"),
        pytest.param("", "", id="empty"),
        pytest.param("/wato/top/hosts.mk", "top", id="top-level"),
    ],
)
def test_folder_path_from_filename(filename: str, expected: str) -> None:
    assert _folder_path_from_filename(filename) == expected


def test_folder_info_from_entry_full() -> None:
    info = _folder_info_from_entry(
        {"path": "dc", "title": "Datacenters", "folder_id": "fid-1", "permitted_groups": ["ops"]}
    )
    assert info == {
        "path": "dc",
        "title": "Datacenters",
        "folder_id": "fid-1",
        "permitted_groups": ["ops"],
    }


def test_folder_info_from_entry_root_without_id() -> None:
    # No folder_id key when the entry carries none (equality pins its absence).
    info = _folder_info_from_entry({"path": "", "title": "Main", "permitted_groups": []})
    assert info == {"path": "", "title": "Main", "permitted_groups": []}


def test_folder_info_from_entry_drops_bad_groups_and_id() -> None:
    info = _folder_info_from_entry(
        {"path": "dc", "title": "DC", "folder_id": "", "permitted_groups": ["ok", 3, None]}
    )
    assert info == {"path": "dc", "title": "DC", "permitted_groups": ["ok"]}


def test_folder_info_from_entry_missing_path_or_title_is_dropped() -> None:
    assert _folder_info_from_entry({"title": "no path"}) is None
    assert _folder_info_from_entry({"path": "dc"}) is None


def test_apply_extra_fills_timing_and_attempt_fields() -> None:
    state = ObjectState(object_id="", type="host", state="UP")
    # offset 5: last_check, next_check, state_type, attempt, max, last_state_change, notif, checks
    row = ["", "", "", "", "", 100.0, 200.0, 1, 2, 3, 50.0, 1, 1]
    result = _apply_extra(state, row, offset=5)
    assert result.last_check == 100.0
    assert result.next_check == 200.0
    assert result.state_type == "HARD"
    assert result.current_attempt == 2
    assert result.max_attempts == 3
    assert result.last_state_change == 50.0


def test_apply_extra_zero_timing_becomes_none() -> None:
    state = ObjectState(object_id="", type="host", state="UP")
    row = ["", "", "", "", "", 0, 0, 0, 1, 1, 0, 1, 1]
    result = _apply_extra(state, row, offset=5)
    assert result.last_check is None
    assert result.next_check is None
    assert result.state_type == "SOFT"


def test_parse_host_state_row_parses_name_and_state() -> None:
    row = ["web01", 1, "DOWN output", "", 0, 0, "10.0.0.1", "Web 01", 0, 0, 1, 1, 1, 0, 1, 1]
    name, state = _parse_host_state_row(row, site_id="muc")
    assert name == "web01"
    assert state.state == "DOWN"
    assert state.output == "DOWN output"
    assert state.address == "10.0.0.1"
    assert state.alias == "Web 01"
    assert state.site_id == "muc"


def test_parse_service_state_row_parses_host_service_key_and_state() -> None:
    row = ["web01", "PING", 2, "CRIT", "rta=5ms", 0, 0, 0, 0, 1, 1, 1, 0, 1, 1]
    key, state = _parse_service_state_row(row)
    assert key == ("web01", "PING")
    assert state.state == "CRITICAL"
    assert state.output == "CRIT"
    assert state.perf_data == "rta=5ms"


def test_build_details_host_with_groups_and_comments() -> None:
    # _HOST_DETAIL_COLS: long_output, check_command, latency, execution_time,
    # is_flapping, in_notif_period, notif_period, check_interval (8 common),
    # then parents, childs, groups, contact_groups, labels
    row = [
        "line1\\nline2",
        "check-mk-host",
        0.5,
        0.1,
        0,
        1,
        "24x7",
        60.0,
        ["parent01"],
        ["child01"],
        ["grp"],
        ["cg"],
        {"env": "prod"},
    ]
    comment_rows = [[1, "admin", "hi", 100.0, 0]]
    details = _build_details("host", "web01", None, row, comment_rows, [])
    assert details.host_name == "web01"
    assert details.long_output == "line1\nline2"
    assert details.check_command == "check-mk-host"
    assert details.parents == ["parent01"]
    assert details.labels == {"env": "prod"}
    assert len(details.comments) == 1
    assert details.comments[0].author == "admin"


def test_build_details_service_uses_service_columns() -> None:
    row = [
        "",
        "check_ping",
        0.0,
        0.0,
        0,
        1,
        "24x7",
        60.0,
        ["hg"],
        ["sg"],
        ["cg"],
        {},
        123.0,
    ]
    details = _build_details("service", "web01", "PING", row, [], [])
    assert details.service_description == "PING"
    assert details.service_groups == ["sg"]
    assert details.last_time_ok == 123.0


def test_default_site_id_explicit_sid_passthrough() -> None:
    assert _default_site_id("muc") == "muc"


def test_default_site_id_falls_back_to_configured_site(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cmk.maps.backend.connections.livestatus.settings.checkmk_site", "central")
    assert _default_site_id(None) == "central"


def test_default_site_id_falls_back_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cmk.maps.backend.connections.livestatus.settings.checkmk_site", "")
    assert _default_site_id(None) == "local"


def _host(state: str, site: str) -> ObjectState:
    return ObjectState(object_id="", type="host", state=state, site_id=site)


def test_worst_state_dict_keeps_worst_on_cross_site_name_collision() -> None:
    # Two sites both expose host 'app01'; the concatenated rows must not let the
    # last (healthy) row overwrite and drop the CRITICAL from the other site.
    merged = _worst_state_dict([("app01", _host("DOWN", "b")), ("app01", _host("UP", "a"))])
    assert merged["app01"].state == "DOWN"
    # Order-independent: worst still wins when the good row arrives first.
    merged_rev = _worst_state_dict([("app01", _host("UP", "a")), ("app01", _host("DOWN", "b"))])
    assert merged_rev["app01"].state == "DOWN"


def test_worst_state_dict_real_state_beats_pending() -> None:
    merged = _worst_state_dict([("h", _host("PENDING", "a")), ("h", _host("UP", "b"))])
    assert merged["h"].state == "UP"
