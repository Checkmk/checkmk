#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio

import pytest

from cmk.maps.backend.connections import livestatus
from cmk.maps.backend.integrations.checkmk_folders import FolderSkeleton
from cmk.maps.backend.schemas.state import ObjectState, ServicesSummary


def _connection(
    monkeypatch: pytest.MonkeyPatch,
    member_rows: list[list[object]],
    service_rows: list[list[object]] | None = None,
) -> tuple[livestatus.LivestatusConnection, list[str]]:
    conn = livestatus.LivestatusConnection(
        socket_path="/var/run/live", host="10.0.0.1", load_folder_perms=FolderSkeleton
    )
    queries: list[str] = []

    async def _query(query: str) -> list[list[object]]:
        queries.append(query)
        if query.startswith(("GET hostgroups", "GET servicegroups")):
            return [["Web servers"]]
        if service_rows is not None and query.startswith("GET services"):
            return service_rows
        return member_rows

    monkeypatch.setattr(conn, "_query", _query)
    return conn, queries


def test_hostgroup_reports_its_hosts_and_on_request_their_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # state, has_been_checked, then ok/warn/crit/unknown/pending service counts per host
    conn, _queries = _connection(monkeypatch, [[0, 1, 3, 1, 0, 0, 0], [1, 1, 2, 0, 1, 0, 0]])

    state = asyncio.run(conn.get_hostgroup_states("web", with_services=True))

    assert state == ObjectState(
        object_id="",
        type="hostgroup",
        state="DOWN",
        alias="Web servers",
        hosts_summary=ServicesSummary(ok=1, critical=1),
        services_summary=ServicesSummary(ok=5, warning=1, critical=1),
    )


def test_hostgroup_leaves_out_the_services_unless_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, queries = _connection(monkeypatch, [[0, 1]])

    state = asyncio.run(conn.get_hostgroup_states("web"))

    assert state.services_summary is None
    assert state.hosts_summary == ServicesSummary(ok=1)
    assert "num_services" not in queries[-1]


def test_hostgroup_reads_hard_states_where_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, queries = _connection(monkeypatch, [[0, 1, 3, 0, 0, 0, 0]])

    asyncio.run(conn.get_hostgroup_states("web", only_hard=True, with_services=True))

    assert "Columns: last_hard_state has_been_checked num_services_hard_ok" in queries[-1]


# A dynamic group is counted by Livestatus, one row per site: pending, then each
# state, then the summed service counts where asked.
def test_dyngroup_reads_hard_states_where_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, queries = _connection(monkeypatch, [[0, 0, 1, 0, 3, 0, 0, 0, 0]])

    state = asyncio.run(
        conn.get_dyngroup_state(
            "host", "Filter: groups >= web\n", only_hard=True, with_services=True
        )
    )

    assert state.state == "DOWN"
    assert state.services_summary == ServicesSummary(ok=3)
    assert "Stats: last_hard_state = 1\n" in queries[-1]
    assert "Stats: sum num_services_hard_ok\n" in queries[-1]


def test_dyngroup_adds_up_what_the_sites_counted(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, queries = _connection(monkeypatch, [[0, 2, 0, 0], [0, 1, 1, 0]])

    state = asyncio.run(conn.get_dyngroup_state("host", "Filter: groups >= web\n"))

    assert state.state == "DOWN"
    assert state.hosts_summary == ServicesSummary(ok=3, critical=1)
    assert "Columns:" not in queries[-1]


def test_a_dyngroup_that_matches_nothing_is_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, _queries = _connection(monkeypatch, [[0, 0, 0, 0, 0]])

    state = asyncio.run(conn.get_dyngroup_state("service", "Filter: groups >= web\n"))

    assert state == ObjectState(object_id="", type="dyngroup", state="PENDING")


def test_dyngroup_leaves_out_the_services_unless_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, queries = _connection(monkeypatch, [[0, 1, 0, 0]])

    state = asyncio.run(conn.get_dyngroup_state("host", "Filter: groups >= web\n"))

    assert state.services_summary is None
    assert state.hosts_summary == ServicesSummary(ok=1)
    assert "num_services" not in queries[-1]


def test_servicegroup_reads_hard_states_where_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, queries = _connection(monkeypatch, [[2, 1]])

    state = asyncio.run(conn.get_servicegroup_states("web", only_hard=True))

    assert state.state == "CRITICAL"
    assert state.alias == "Web servers"
    assert "Columns: last_hard_state has_been_checked\n" in queries[-1]


# The core reports a member never checked as state 0, which would read as UP / OK.
def test_hostgroup_counts_hosts_never_checked_as_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, _queries = _connection(monkeypatch, [[0, 1], [0, 0]])

    state = asyncio.run(conn.get_hostgroup_states("web"))

    assert state.hosts_summary == ServicesSummary(ok=1, pending=1)


def test_a_group_of_hosts_never_checked_is_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, _queries = _connection(monkeypatch, [[1, 0, 0, 0]])

    assert asyncio.run(conn.get_dyngroup_state("host", "Filter: groups >= web\n")).state == (
        "PENDING"
    )


def test_servicegroup_counts_services_never_checked_as_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn, _queries = _connection(monkeypatch, [[0, 1], [0, 0]])

    state = asyncio.run(conn.get_servicegroup_states("web"))

    assert state.services_summary == ServicesSummary(ok=1, pending=1)


def test_dyngroup_counts_services_never_checked_as_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn, _queries = _connection(monkeypatch, [[1, 0, 0, 1, 0]])

    state = asyncio.run(conn.get_dyngroup_state("service", "Filter: groups >= web\n"))

    assert state.state == "CRITICAL"
    assert state.services_summary == ServicesSummary(critical=1, pending=1)


def test_hostgroup_leaves_out_the_hosts_that_match(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, queries = _connection(monkeypatch, [[0, 1]])

    asyncio.run(conn.get_hostgroup_states("web", exclude="^test-"))

    assert queries[-1].endswith("Filter: groups >= web\nFilter: name !~~ ^test-\n")


def test_hostgroup_leaves_out_services_by_host_and_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # state, has_been_checked per service
    conn, queries = _connection(
        monkeypatch, [[0, 1, 3, 1, 0, 0, 0]], service_rows=[[0, 1], [2, 1], [0, 0]]
    )

    state = asyncio.run(
        conn.get_hostgroup_states("web", with_services=True, exclude="^web-01~~^CPU")
    )

    assert state.services_summary == ServicesSummary(ok=1, critical=1, pending=1)
    assert "!~~" not in queries[-2]
    assert queries[-1].endswith(
        "Filter: host_groups >= web\nFilter: host_name !~~ ^web-01\n"
        "Filter: description !~~ ^CPU\nOr: 2\n"
    )


def test_servicegroup_leaves_out_the_services_that_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn, queries = _connection(monkeypatch, [[0, 1]])

    asyncio.run(conn.get_servicegroup_states("web", exclude="^test-"))

    assert queries[-1].endswith("Filter: groups >= web\nFilter: host_name !~~ ^test-\n")


def test_hosts_services_summaries_leave_out_the_services_that_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # host_name, state, has_been_checked per service
    conn, queries = _connection(monkeypatch, [["web-01", 1, 1], ["web-01", 0, 1], ["web-02", 0, 0]])

    summaries = asyncio.run(conn.get_hosts_services_summaries(["web-01", "web-02", "db"], "^CPU"))

    assert summaries == {
        "web-01": ServicesSummary(ok=1, warning=1),
        "web-02": ServicesSummary(pending=1),
        "db": ServicesSummary(),
    }
    assert queries[-1].endswith(
        "Filter: host_name = web-01\nFilter: host_name = web-02\nFilter: host_name = db\n"
        "Or: 3\nFilter: description !~~ ^CPU\n"
    )


def test_hosts_services_summaries_ignore_a_service_pattern(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn, queries = _connection(monkeypatch, [])

    assert asyncio.run(conn.get_hosts_services_summaries(["web-01"], "web-01~~^CPU")) is None
    assert queries == []
