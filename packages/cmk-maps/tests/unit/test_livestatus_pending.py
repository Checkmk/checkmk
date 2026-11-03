#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio

import pytest

from cmk.maps.backend.connections import livestatus


async def _no_folders() -> list[object]:
    return []


def _connection(
    monkeypatch: pytest.MonkeyPatch, rows: list[list[object]]
) -> livestatus.LivestatusConnection:
    monkeypatch.setattr(livestatus, "_load_wato_folders", _no_folders)
    conn = livestatus.LivestatusConnection(socket_path="/var/run/live", host="10.0.0.1")

    async def _query(_query: str) -> list[list[object]]:
        return rows

    async def _query_with_site(_query: str) -> list[tuple[str, list[object]]]:
        return [("central", row) for row in rows]

    monkeypatch.setattr(conn, "_query", _query)
    monkeypatch.setattr(conn, "_query_with_site", _query_with_site)
    return conn


def test_topology_reads_a_never_checked_host_as_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    # name, parents, state, has_been_checked, then output .. service counts
    row: list[object] = ["new-host", [], 0, 0, "", "", "", 0, 0, 0, 0, 1, 1, 1, 0, 1, 1]
    conn = _connection(monkeypatch, [row + [0, 0, 0, 0, 0]])

    [host] = asyncio.run(conn.get_topology())

    assert host["state"] == "PENDING"


def test_host_services_read_a_never_checked_service_as_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # description, state, has_been_checked, output, ack, downtime, last change, flapping
    conn = _connection(monkeypatch, [["CPU load", 0, 0, "", 0, 0, 0, 0]])

    [service] = asyncio.run(conn.get_host_services("web01"))

    assert service["state"] == "PENDING"


def test_service_search_reads_a_never_checked_service_as_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # host, description, state, has_been_checked, output, ack, downtime, last change, flapping
    conn = _connection(monkeypatch, [["web01", "CPU load", 0, 0, "", 0, 0, 0, 0]])

    [match] = asyncio.run(
        conn.search_services(host_terms=[], service_terms=["cpu"], any_terms=[], limit=10)
    )

    assert match["state"] == "PENDING"
