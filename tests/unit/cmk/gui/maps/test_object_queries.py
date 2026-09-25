#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the GUI-owned on-demand object queries (``_object_queries``)."""

from collections.abc import Sequence

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.maps.gui import _object_queries
from cmk.maps.gui._object_queries import GeoCoordinates, Member, PerfMetricsSource


class _FakeLive:
    """Enough of MultiSiteConnection for ``Query`` to run against canned rows.

    ``Query.iterate`` reads ``prepend_site`` and zips the positional rows from
    ``query()`` with the queried column names, so the fixtures below stay
    positional while the code under test reads the rows by name.
    """

    prepend_site = False

    def __init__(self, rows: Sequence[object]) -> None:
        self._rows = rows
        self.queries: list[str] = []

    def query(self, lql: str) -> Sequence[object]:
        self.queries.append(lql)
        return self._rows

    def set_only_sites(self, _sites: object = None) -> None:
        pass


def _patch_live(monkeypatch: pytest.MonkeyPatch, rows: Sequence[object]) -> _FakeLive:
    live = _FakeLive(rows)
    monkeypatch.setattr(_object_queries, "live", lambda: live)
    return live


def test_host_geo_from_maps_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live(monkeypatch, [[{"maps_lat": "51.0", "maps_lng": "10.0"}, [], []]])
    assert _object_queries.host_geo("h") == GeoCoordinates(lat=51.0, lng=10.0)


def test_host_geo_falls_back_to_legacy_custom_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live(monkeypatch, [[{}, ["LAT", "LONG"], ["48.1", "11.5"]]])
    assert _object_queries.host_geo("h") == GeoCoordinates(lat=48.1, lng=11.5)


def test_host_geo_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live(monkeypatch, [[{}, [], []]])
    assert _object_queries.host_geo("h") is None


def test_host_geo_none_when_no_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live(monkeypatch, [])
    assert _object_queries.host_geo("h") is None


def test_host_geo_none_on_unparseable_coords(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live(monkeypatch, [[{"maps_lat": "x", "maps_lng": "y"}, [], []]])
    assert _object_queries.host_geo("h") is None


def test_host_geo_filters_by_host_name(monkeypatch: pytest.MonkeyPatch) -> None:
    live = _patch_live(monkeypatch, [[{}, [], []]])
    _object_queries.host_geo("h1")
    assert live.queries == [
        "GET hosts\nColumns: labels custom_variable_names custom_variable_values\nFilter: name = h1"
    ]


def test_perf_metrics_service_returns_perfdata_and_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_live(monkeypatch, [["rta=0.5;;", "check_icmp"]])
    assert _object_queries.perf_metrics("h", "PING") == PerfMetricsSource(
        perf_data="rta=0.5;;", check_command="check_icmp", metrics=["rta"]
    )


def test_perf_metrics_keeps_quoted_labels_with_spaces(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live(monkeypatch, [["rta=0.5ms;; 'pl rate'=0%;;", "check_icmp"]])
    assert _object_queries.perf_metrics("h", "PING").metrics == ["rta", "pl rate"]


def test_perf_metrics_host_has_no_check_command(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live(monkeypatch, [["rta=0.5;;"]])
    result = _object_queries.perf_metrics("h", None)
    assert result.check_command == ""
    assert result.metrics == ["rta"]


def test_group_members_maps_host_state_and_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live(monkeypatch, [["h1", 1, "DOWN - unreachable\nline2", 1, 0, 1, 123.0]])
    assert _object_queries.group_members("hostgroup", "linux") == [
        Member(
            host="h1",
            service="",
            state="DOWN",
            output="DOWN - unreachable",
            acknowledged=True,
            in_downtime=False,
            notifications_enabled=True,
            last_state_change=123.0,
        )
    ]


def test_group_members_filters_by_group_membership(monkeypatch: pytest.MonkeyPatch) -> None:
    # ``groups >= <name>`` is the list-membership filter, not a string compare.
    live = _patch_live(monkeypatch, [])
    _object_queries.group_members("hostgroup", "linux")
    assert live.queries[0].endswith("Filter: groups >= linux")


def test_group_members_unknown_type_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live(monkeypatch, [["h1", 0, "", 0, 0, 1, 0]])
    assert _object_queries.group_members("nope", "linux") == []


def test_dyngroup_members_splices_the_checked_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    live = _patch_live(monkeypatch, [])
    _object_queries.dyngroup_members("host", "Filter: state = 1")
    assert live.queries[0].endswith("Filter: state = 1")


def test_dyngroup_members_rejects_unsafe_filter() -> None:
    with pytest.raises(MKUserError):
        _object_queries._checked_object_filter("GET hosts\nColumns: name")  # noqa: SLF001


def test_dyngroup_members_normalizes_safe_filter() -> None:
    assert _object_queries._checked_object_filter("Filter: state = 1") == "Filter: state = 1\n"  # noqa: SLF001
