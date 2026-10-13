#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio

import pytest

from cmk.maps.backend.connections import livestatus
from cmk.maps.backend.schemas.state import ObjectState, ServicesSummary


async def _no_folders() -> list[object]:
    return []


def _connection(
    monkeypatch: pytest.MonkeyPatch, member_rows: list[list[object]]
) -> tuple[livestatus.LivestatusConnection, list[str]]:
    monkeypatch.setattr(livestatus, "_load_wato_folders", _no_folders)
    conn = livestatus.LivestatusConnection(socket_path="/var/run/live", host="10.0.0.1")
    queries: list[str] = []

    async def _query(query: str) -> list[list[object]]:
        queries.append(query)
        return (
            [["web"]] if query.startswith(("GET hostgroups", "GET servicegroups")) else member_rows
        )

    monkeypatch.setattr(conn, "_query", _query)
    return conn, queries


def test_hostgroup_reports_its_hosts_and_on_request_their_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # state, then ok/warn/crit/unknown/pending service counts per host
    conn, _queries = _connection(monkeypatch, [[0, 3, 1, 0, 0, 0], [1, 2, 0, 1, 0, 0]])

    state = asyncio.run(conn.get_hostgroup_states("web", with_services=True))

    assert state == ObjectState(
        object_id="",
        type="hostgroup",
        state="DOWN",
        hosts_summary=ServicesSummary(ok=1, critical=1),
        services_summary=ServicesSummary(ok=5, warning=1, critical=1),
    )


def test_hostgroup_leaves_out_the_services_unless_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, queries = _connection(monkeypatch, [[0]])

    state = asyncio.run(conn.get_hostgroup_states("web"))

    assert state.services_summary is None
    assert state.hosts_summary == ServicesSummary(ok=1)
    assert "num_services" not in queries[-1]


def test_hostgroup_reads_hard_states_where_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, queries = _connection(monkeypatch, [[0, 3, 0, 0, 0, 0]])

    asyncio.run(conn.get_hostgroup_states("web", only_hard=True, with_services=True))

    assert "Columns: last_hard_state num_services_hard_ok" in queries[-1]


def test_servicegroup_reads_hard_states_where_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    conn, queries = _connection(monkeypatch, [[2]])

    state = asyncio.run(conn.get_servicegroup_states("web", only_hard=True))

    assert state.state == "CRITICAL"
    assert "Columns: last_hard_state\n" in queries[-1]
