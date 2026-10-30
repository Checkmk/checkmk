#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio

import pytest

from cmk.livestatus_client import MKLivestatusSocketError
from cmk.maps.backend.connections import livestatus
from cmk.maps.backend.connections.base import QueryTimeoutError
from cmk.maps.backend.integrations.checkmk_folders import FolderSkeleton


def _connection(
    monkeypatch: pytest.MonkeyPatch, rows: list[list[object]]
) -> tuple[livestatus.LivestatusConnection, list[str]]:
    conn = livestatus.LivestatusConnection(
        socket_path="/var/run/live", host="10.0.0.1", load_folder_perms=FolderSkeleton
    )
    queries: list[str] = []

    async def _query_with_site(query: str) -> list[tuple[str | None, list[object]]]:
        queries.append(query)
        return [("central", row) for row in rows]

    monkeypatch.setattr(conn, "_query_with_site", _query_with_site)
    return conn, queries


def test_the_filter_combines_only_its_own_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, queries = _connection(monkeypatch, [])

    asyncio.run(
        conn.get_filter_members(
            "host", "Filter: name = a\nFilter: name = b\nOr: 2\nNegate:\n", limit=1000
        )
    )

    assert queries[0].startswith("GET hosts\nColumns: name state ")
    assert queries[0].endswith("Filter: name = a\nFilter: name = b\nOr: 2\nNegate:\nLimit: 1001\n")


def test_hard_states_choose_the_column_and_never_filter_members(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn, queries = _connection(monkeypatch, [])

    asyncio.run(conn.get_filter_members("service", None, only_hard=True, limit=10))

    assert "Columns: host_name description last_hard_state " in queries[0]
    assert "Filter:" not in queries[0]


def test_members_name_the_service_they_stand_for(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, _queries = _connection(monkeypatch, [["web-1", "HTTP", 2, "CRIT - down", "", 0, 0]])

    members = asyncio.run(conn.get_filter_members("service", None, limit=10))

    state = members[("web-1", "HTTP")]
    assert (state.host_name, state.service_description) == ("web-1", "HTTP")


def test_a_grid_past_its_limit_keeps_the_members_with_a_problem_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = livestatus.LivestatusConnection(
        socket_path="/var/run/live", host="10.0.0.1", load_folder_perms=FolderSkeleton
    )
    queries: list[str] = []

    async def _query_with_site(query: str) -> list[tuple[str | None, list[object]]]:
        queries.append(query)
        if "worst_service_state" in query:
            return [("central", ["zz-down", 1, "", "", 0, 0])]
        return [("central", [name, 0, "", "", 0, 0]) for name in ("a", "b", "c")]

    monkeypatch.setattr(conn, "_query_with_site", _query_with_site)

    members = asyncio.run(conn.get_filter_members("host", None, with_services=True, limit=2))

    assert list(members) == [("zz-down", None), ("a", None), ("b", None)]
    assert queries[1].endswith(
        "Filter: state != 0\nFilter: worst_service_state != 0\nOr: 2\nLimit: 3\n"
    )


def test_a_grid_past_its_limit_keeps_one_more_member_than_its_limit_over_all_sites(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = livestatus.LivestatusConnection(
        socket_path="/var/run/live", host="10.0.0.1", load_folder_perms=FolderSkeleton
    )

    async def _query_with_site(query: str) -> list[tuple[str | None, list[object]]]:
        if "Filter: state != 0" in query:
            return []
        return [
            (site, [f"{site}-{n}", 0, "", "", 0, 0]) for site in ("east", "west") for n in (1, 2, 3)
        ]

    monkeypatch.setattr(conn, "_query_with_site", _query_with_site)

    members = asyncio.run(conn.get_filter_members("host", None, limit=2))

    assert list(members) == [("east-1", None), ("east-2", None), ("east-3", None)]


def test_host_members_come_with_the_counts_of_their_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row: list[object] = ["web-1", 0, "", "", 0, 0, *[""] * 13, 3, 1, 2, 0, 0]
    conn, queries = _connection(monkeypatch, [row])

    members = asyncio.run(conn.get_filter_members("host", None, limit=10))

    summary = members[("web-1", None)].services_summary
    assert summary is not None
    assert (summary.ok, summary.warning, summary.critical) == (3, 1, 2)
    assert "staleness num_services_ok num_services_warn " in queries[0]


def test_host_members_with_hard_states_count_hard_service_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn, queries = _connection(monkeypatch, [])

    asyncio.run(conn.get_filter_members("host", None, only_hard=True, limit=10))

    assert "num_services_hard_ok num_services_hard_warn " in queries[0]


def _failing_problems(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> tuple[livestatus.LivestatusConnection, list[str]]:
    conn = livestatus.LivestatusConnection(
        socket_path="/var/run/live", host="10.0.0.1", load_folder_perms=FolderSkeleton
    )
    queries: list[str] = []

    async def _query_with_site(query: str) -> list[tuple[str | None, list[object]]]:
        queries.append(query)
        if "Filter: state != 0" in query:
            raise error
        return [("central", [name, 0, "", "", 0, 0]) for name in ("c", "a", "b")]

    monkeypatch.setattr(conn, "_query_with_site", _query_with_site)
    return conn, queries


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(QueryTimeoutError(), id="timed-out"),
        pytest.param(MKLivestatusSocketError("socket closed"), id="socket-closed"),
    ],
)
def test_a_grid_past_its_limit_is_cut_by_name_when_the_problems_query_fails(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    conn, _queries = _failing_problems(monkeypatch, error)

    members = asyncio.run(conn.get_filter_members("host", None, limit=2))

    assert list(members) == [("a", None), ("b", None), ("c", None)]


def test_a_problems_query_that_timed_out_is_not_sent_again_on_the_next_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn, queries = _failing_problems(monkeypatch, QueryTimeoutError())

    asyncio.run(conn.get_filter_members("host", None, limit=2))
    asyncio.run(conn.get_filter_members("host", None, limit=2))

    assert sum("Filter: state != 0" in query for query in queries) == 1
