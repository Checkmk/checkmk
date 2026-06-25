#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Daemon state-resolution core: primary-host auto-binding + state roll-up.

Covers the worst-state combination logic (host state vs its service-summary
counts), the worst-first service ordering shared by lazy-expand and search, the
folder slug/title normalisers, and the ``auto_host`` primary-host resolution
that lets shipped/template presentation maps show live data on a fresh
install without a hard-coded host name.
"""

import asyncio
from typing import cast
from unittest.mock import AsyncMock

import pytest

from cmk.maps.backend.connections.base import ConnectionBase
from cmk.maps.backend.core.config import settings
from cmk.maps.backend.schemas.state import FolderHostService, ServicesSummary
from cmk.maps.backend.services import state_service
from cmk.maps.shared.states import severity_rank


def _connection(hosts: dict[str, object]) -> ConnectionBase:
    conn = AsyncMock()
    conn.get_all_hosts_states = AsyncMock(return_value=hosts)
    return cast(ConnectionBase, conn)


def test_resolve_primary_host_prefers_site_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "checkmk_site", "mysite")
    conn = _connection({"alpha": object(), "mysite": object(), "localhost": object()})
    assert asyncio.run(state_service._resolve_primary_host(conn)) == "mysite"  # noqa: SLF001


def test_resolve_primary_host_falls_back_to_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "checkmk_site", "absent")
    conn = _connection({"zeta": object(), "localhost": object(), "alpha": object()})
    assert asyncio.run(state_service._resolve_primary_host(conn)) == "localhost"  # noqa: SLF001


def test_resolve_primary_host_falls_back_to_first_alphabetical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "checkmk_site", "absent")
    conn = _connection({"zeta": object(), "beta": object(), "alpha": object()})
    assert asyncio.run(state_service._resolve_primary_host(conn)) == "alpha"  # noqa: SLF001


def test_resolve_primary_host_empty_site_returns_none() -> None:
    conn = _connection({})
    assert asyncio.run(state_service._resolve_primary_host(conn)) is None  # noqa: SLF001


def test_resolve_primary_host_swallows_connection_error() -> None:
    conn = AsyncMock()
    conn.get_all_hosts_states = AsyncMock(side_effect=RuntimeError("livestatus down"))
    assert asyncio.run(state_service._resolve_primary_host(cast(ConnectionBase, conn))) is None  # noqa: SLF001


def test_severity_rank_orders_states_worst_highest() -> None:
    rank = severity_rank
    assert rank("CRITICAL") > rank("WARNING") > rank("UNKNOWN") > rank("OK")
    assert rank("DOWN") > rank("UP")
    # Unknown/empty states sink below OK so they never win a worst-state roll-up.
    assert rank("PENDING") == -1
    assert rank("nonsense") == -1


def test_combined_state_takes_worst_of_host_and_services() -> None:
    combined = state_service._combined_state_from_summary  # noqa: SLF001
    # No summary → the host state stands.
    assert combined("UP", None) == "UP"
    # A CRITICAL service worsens an UP host.
    assert combined("UP", ServicesSummary(critical=1)) == "CRITICAL"
    assert combined("UP", ServicesSummary(warning=2)) == "WARNING"
    assert combined("UP", ServicesSummary(unknown=1)) == "UNKNOWN"
    # A DOWN host already outranks a mere WARNING service — host state wins.
    assert combined("DOWN", ServicesSummary(warning=3)) == "DOWN"
    # All-OK services leave the host state untouched.
    assert combined("UP", ServicesSummary(ok=5)) == "UP"


def test_sort_folder_services_worst_first_then_alphabetical() -> None:
    services = [
        FolderHostService(name="b-ok", state="OK"),
        FolderHostService(name="a-crit", state="CRITICAL"),
        FolderHostService(name="c-crit", state="CRITICAL"),
        FolderHostService(name="a-warn", state="WARNING"),
    ]
    state_service.sort_folder_services(services)
    assert [s.name for s in services] == ["a-crit", "c-crit", "a-warn", "b-ok"]


@pytest.mark.parametrize(
    "slug, expected",
    [
        ("", "Main"),
        ("data_center-eu", "Data Center Eu"),
        ("prod", "Prod"),
    ],
)
def test_prettify_folder_title(slug: str, expected: str) -> None:
    assert state_service._prettify_folder_title(slug) == expected  # noqa: SLF001


@pytest.mark.parametrize(
    "path, expected",
    [("/a/b/", "a/b"), ("a/b", "a/b"), ("/", ""), ("", "")],
)
def test_norm_folder_path_strips_slashes(path: str, expected: str) -> None:
    assert state_service._norm_folder_path(path) == expected  # noqa: SLF001
