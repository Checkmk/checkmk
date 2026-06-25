#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Runtime adoption of the distributed site specs by a running daemon.

``LivestatusConnection`` resolves its fan-out set once at construction. These
tests pin that a federation-eligible connection (one pointing at the central
site's own local socket) still switches to multisite when the prepared
``sitespecs.mk`` appears *after* startup — without a restart — while an
explicitly targeted (TCP) connection never does.

The second group pins the per-site *trust* path in ``get_folder_tree``: when a
federation site stops answering it silently drops out of the MultiSiteConnection
result, so the daemon replays that site's last-known host rows marked ``stale``
(and reports it in ``dead_sites``) instead of letting the map read "all green".
That replay cache is auth-scoped, so one contact-scoped user can never see
another's cached rows.
"""

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from cmk.maps.backend.connections import livestatus
from cmk.maps.backend.connections.base import FolderTreeData
from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations import checkmk_sites


def _local_socket_path(omd_root: Path) -> str:
    return str(omd_root / "tmp" / "run" / "live")


def test_adopts_sites_when_specs_appear_after_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "checkmk_omd_root", str(tmp_path))

    # Specs absent at construction -> the connection starts on the single-socket
    # path even though it is eligible to federate.
    monkeypatch.setattr(checkmk_sites, "sites_mk_mtime", lambda: 0.0)
    monkeypatch.setattr(checkmk_sites, "load_sites", lambda: None)
    conn = livestatus.LivestatusConnection(socket_path=_local_socket_path(tmp_path), host=None)
    assert conn._federation_eligible is True  # noqa: SLF001
    assert not conn._sites  # noqa: SLF001

    # The GUI writes the specs while the daemon runs; the next query-time check
    # picks them up and flips the connection to multisite.
    monkeypatch.setattr(checkmk_sites, "sites_mk_mtime", lambda: 123.0)
    monkeypatch.setattr(checkmk_sites, "load_sites", lambda: {"central": {}, "remote1": {}})
    conn._adopt_sites_if_appeared()  # noqa: SLF001
    assert conn._sites == {"central": {}, "remote1": {}}  # noqa: SLF001


def test_unchanged_mtime_is_not_reparsed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr(checkmk_sites, "sites_mk_mtime", lambda: 0.0)
    monkeypatch.setattr(checkmk_sites, "load_sites", lambda: None)
    conn = livestatus.LivestatusConnection(socket_path=_local_socket_path(tmp_path), host=None)

    calls = 0

    def _counting_load() -> dict[str, dict[str, object]]:
        nonlocal calls
        calls += 1
        return {"central": {}, "remote1": {}}

    monkeypatch.setattr(checkmk_sites, "sites_mk_mtime", lambda: 7.0)
    monkeypatch.setattr(checkmk_sites, "load_sites", _counting_load)

    conn._adopt_sites_if_appeared()  # noqa: SLF001
    conn._adopt_sites_if_appeared()  # second call: already adopted -> no reparse  # noqa: SLF001
    assert calls == 1


def test_explicit_tcp_target_never_federates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "checkmk_omd_root", str(tmp_path))
    # Specs are present and non-empty, but an explicitly targeted TCP connection
    # is a deliberate single-site pick and must not silently fan out.
    monkeypatch.setattr(checkmk_sites, "sites_mk_mtime", lambda: 123.0)
    monkeypatch.setattr(checkmk_sites, "load_sites", lambda: {"central": {}, "remote1": {}})
    conn = livestatus.LivestatusConnection(socket_path="/var/run/live", host="10.0.0.1")
    assert conn._federation_eligible is False  # noqa: SLF001
    assert conn._sites is None  # noqa: SLF001

    conn._adopt_sites_if_appeared()  # noqa: SLF001
    assert conn._sites is None  # noqa: SLF001


# --------------------------------------------------------------------------- #
# Per-site trust: dead-site stale replay in get_folder_tree
# --------------------------------------------------------------------------- #


async def _no_folders() -> list[object]:
    """Skip the GUI-prepared folder skeleton (file access) — irrelevant here."""
    return []


def _host_row(name: str, *, state: int = 0, filename: str = "") -> list[object]:
    """One ``GET hosts`` row in the column order ``get_folder_tree`` reads:
    name, filename, state, output, ack, downtime, 5×num_services_*, is_flapping,
    last_state_change."""
    return [name, filename, state, f"OK - {name}", 0, 0, 3, 0, 0, 0, 0, 0, None]


def _rows_from(
    tagged: list[tuple[str, list[object]]],
) -> Callable[[str], Awaitable[list[tuple[str, list[object]]]]]:
    """A fake ``_query_with_site`` returning the given (site_id, row) tuples."""

    async def _fake(_query: str) -> list[tuple[str, list[object]]]:
        return tagged

    return _fake


def _tcp_connection(monkeypatch: pytest.MonkeyPatch) -> livestatus.LivestatusConnection:
    """A non-federated (TCP) connection — construction touches no site files.
    Federation state is then set explicitly per test via ``_sites``/``_mc_dead``."""
    monkeypatch.setattr(livestatus, "_load_wato_folders", _no_folders)
    return livestatus.LivestatusConnection(socket_path="/var/run/live", host="10.0.0.1")


def _fetch_tree_as(conn: livestatus.LivestatusConnection, auth_user: str | None) -> FolderTreeData:
    """Run ``get_folder_tree`` inside *auth_user*'s scope (the replay cache key)."""

    async def _coro() -> FolderTreeData:
        token = livestatus._auth_user_ctx.set(auth_user)  # noqa: SLF001
        try:
            return await conn.get_folder_tree()
        finally:
            livestatus._auth_user_ctx.reset(token)  # noqa: SLF001

    return asyncio.run(_coro())


def _staleness(tree: FolderTreeData) -> tuple[set[str], set[str]]:
    live = {h["host_name"] for h in tree.hosts if not h.get("stale")}
    stale = {h["host_name"] for h in tree.hosts if h.get("stale")}
    return live, stale


def test_dead_federation_site_rows_are_replayed_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = _tcp_connection(monkeypatch)
    conn._sites = {"central": {}, "remote_fra": {}}  # federation active  # noqa: SLF001

    # First fetch: both sites answer, none dead -> cache primed, nothing stale.
    conn._mc_dead = set()  # noqa: SLF001
    monkeypatch.setattr(
        conn,
        "_query_with_site",
        _rows_from([("central", _host_row("central-h")), ("remote_fra", _host_row("remote-h"))]),
    )
    first = asyncio.run(conn.get_folder_tree())
    assert first.dead_sites == []
    live, stale = _staleness(first)
    assert live == {"central-h", "remote-h"}
    assert stale == set()

    # Second fetch: remote_fra died -> the MC drops it, only central answers. The
    # dead site's last-known rows are replayed (marked stale) and reported so the
    # map greys them out instead of showing them healthy/gone.
    conn._mc_dead = {"remote_fra"}  # noqa: SLF001
    monkeypatch.setattr(conn, "_query_with_site", _rows_from([("central", _host_row("central-h"))]))
    second = asyncio.run(conn.get_folder_tree())
    assert second.dead_sites == ["remote_fra"]
    live, stale = _staleness(second)
    assert live == {"central-h"}
    assert stale == {"remote-h"}


def test_dead_site_replay_is_scoped_to_the_auth_user(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = _tcp_connection(monkeypatch)
    conn._sites = {"central": {}, "remote_fra": {}}  # noqa: SLF001

    # Alice primes her scope's cache while remote_fra is alive.
    conn._mc_dead = set()  # noqa: SLF001
    monkeypatch.setattr(
        conn, "_query_with_site", _rows_from([("remote_fra", _host_row("alice-only-h"))])
    )
    _fetch_tree_as(conn, "alice")

    # remote_fra dies. Bob — a different contact scope with no prior successful
    # fetch — sees the site reported dead but must NOT get Alice's cached rows.
    conn._mc_dead = {"remote_fra"}  # noqa: SLF001
    monkeypatch.setattr(conn, "_query_with_site", _rows_from([]))
    bob_tree = _fetch_tree_as(conn, "bob")
    assert bob_tree.dead_sites == ["remote_fra"]
    assert bob_tree.hosts == []  # no cross-user replay

    # Alice still gets her own cached rows replayed under her scope.
    alice_tree = _fetch_tree_as(conn, "alice")
    _, stale = _staleness(alice_tree)
    assert stale == {"alice-only-h"}


def test_single_site_connection_never_reports_dead_sites(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = _tcp_connection(monkeypatch)
    assert conn._sites is None  # not federated  # noqa: SLF001

    # Even with a populated dead set, a non-federated connection has no sites to
    # declare dead — dead_sites stays empty.
    conn._mc_dead = {"phantom"}  # noqa: SLF001
    monkeypatch.setattr(conn, "_query_with_site", _rows_from([("central", _host_row("h"))]))
    tree = asyncio.run(conn.get_folder_tree())
    assert tree.dead_sites == []
    live, stale = _staleness(tree)
    assert live == {"h"}
    assert stale == set()
