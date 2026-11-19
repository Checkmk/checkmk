#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio

import pytest

from cmk.maps.backend.connections import livestatus
from cmk.maps.backend.integrations.checkmk_folders import FolderSkeleton
from cmk.maps.backend.schemas.state import ServicesSummary


def _connection(
    monkeypatch: pytest.MonkeyPatch, rows: list[list[object]], queries: list[str] | None = None
) -> livestatus.LivestatusConnection:
    conn = livestatus.LivestatusConnection(
        socket_path="/var/run/live", host="10.0.0.1", load_folder_perms=FolderSkeleton
    )

    async def _query_with_site(query: str) -> list[tuple[str | None, list[object]]]:
        if queries is not None:
            queries.append(query)
        return [(None, row) for row in rows]

    monkeypatch.setattr(conn, "_query_with_site", _query_with_site)
    return conn


def test_only_the_services_asked_for_are_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    # host_name, description, state: the query matches each host's services by
    # all the names asked for
    conn = _connection(
        monkeypatch,
        [["web-01", "CPU", 2], ["web-01", "Disk", 0], ["web-02", "CPU", 0], ["web-02", "Disk", 1]],
    )

    states = asyncio.run(conn.get_services_states([("web-01", "CPU"), ("web-02", "Disk")]))

    assert {key: state.state for key, state in states.items()} == {
        ("web-01", "CPU"): "CRITICAL",
        ("web-02", "Disk"): "WARNING",
    }


def test_services_are_asked_for_by_the_hosts_that_have_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queries: list[str] = []
    conn = _connection(monkeypatch, [], queries)

    asyncio.run(conn.get_services_states([("web-01", "CPU"), ("web-02", "Disk")]))

    assert queries[0].endswith(
        "Filter: host_name ~ ^(?:web\\-01|web\\-02)$\n"
        "Filter: description ~ ^(?:CPU|Disk)$\n"
        "Filter: host_name = web-01\nFilter: description = CPU\nAnd: 2\n"
        "Filter: host_name = web-02\nFilter: description = Disk\nAnd: 2\n"
        "Or: 2\n"
    )


def test_services_summary_counts_nothing_for_a_host_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # name, then ok/warn/crit/unknown/pending service counts
    conn = _connection(monkeypatch, [["web-01", 3, 1, 0, 0, 0]])

    summaries = asyncio.run(conn.get_services_summary(["web-01", "web-02"]))

    assert summaries == {"web-01": ServicesSummary(ok=3, warning=1), "web-02": ServicesSummary()}


def test_service_search_drops_a_line_break_from_a_term(monkeypatch: pytest.MonkeyPatch) -> None:
    queries: list[str] = []
    conn = _connection(monkeypatch, [], queries)

    asyncio.run(
        conn.search_services(host_terms=[], service_terms=["c\npu"], any_terms=[], limit=10)
    )

    assert "Filter: description ~~ cpu\n" in queries[0]
