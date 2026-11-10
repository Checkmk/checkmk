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
import logging
import socket
import threading
from collections.abc import Awaitable, Callable, Iterator
from pathlib import Path

import pytest

from cmk.livestatus_client import MKLivestatusQueryError
from cmk.maps.backend.connections import livestatus
from cmk.maps.backend.connections.base import FolderTreeData, MonitoringScope, QueryRefusedError
from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations import checkmk_sites
from cmk.maps.backend.integrations.checkmk import FolderScope


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


def test_a_user_who_may_not_see_the_own_site_gets_no_rows_from_its_socket(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr(checkmk_sites, "load_sites", lambda: None)
    conn = livestatus.LivestatusConnection(socket_path=_local_socket_path(tmp_path), host=None)
    connected: list[bool] = []

    def _connect() -> object:
        connected.append(True)
        raise ConnectionRefusedError

    monkeypatch.setattr(conn, "_make_singlesite_connection", _connect)
    token = livestatus._scope_ctx.set(MonitoringScope("alice", frozenset({"other"})))  # noqa: SLF001
    try:
        rows = conn._run_singlesite_sync("GET hosts\nColumns: name\n")  # noqa: SLF001
    finally:
        livestatus._scope_ctx.reset(token)  # noqa: SLF001

    assert (rows, connected) == ([], [])


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


async def _no_folders() -> livestatus.WatoFolders:
    """Skip the GUI-prepared folder skeleton (file access) — irrelevant here."""
    return livestatus.WatoFolders([], hide_unreadable=False)


def _host_row(
    name: str, *, state: int = 0, filename: str = "", checked: bool = True
) -> list[object]:
    """One ``GET hosts`` row in the column order ``get_folder_tree`` reads:
    name, filename, state, output, ack, downtime, 5×num_services_*, is_flapping,
    last_state_change, has_been_checked."""
    return [name, filename, state, f"OK - {name}", 0, 0, 3, 0, 0, 0, 0, 0, None, int(checked)]


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
        token = livestatus._scope_ctx.set(MonitoringScope(auth_user))  # noqa: SLF001
        try:
            return await conn.get_folder_tree()
        finally:
            livestatus._scope_ctx.reset(token)  # noqa: SLF001

    return asyncio.run(_coro())


def test_a_folder_tree_without_a_folder_scope_permits_no_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _tcp_connection(monkeypatch)

    async def _folders() -> livestatus.WatoFolders:
        return livestatus.WatoFolders(
            [{"path": "dc", "title": "DC", "permitted_groups": []}], hide_unreadable=False
        )

    monkeypatch.setattr(livestatus, "_load_wato_folders", _folders)
    monkeypatch.setattr(conn, "_query_with_site", _rows_from([]))

    tree = asyncio.run(conn.get_folder_tree())

    assert {f["path"]: f.get("permitted") for f in tree.folders}["dc"] is False


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


def _stale_after_remote_died(
    conn: livestatus.LivestatusConnection,
    monkeypatch: pytest.MonkeyPatch,
    *,
    primed: tuple[FolderScope | None, bool],
    asked: tuple[FolderScope | None, bool],
) -> set[str]:
    """The stale hosts of a request ``asked`` after one ``primed`` while the remote site lived."""

    async def _tree(folder_scope: FolderScope | None, only_hard: bool) -> FolderTreeData:
        async with conn.with_folder_scope(folder_scope):
            return await conn.get_folder_tree(only_hard=only_hard)

    conn._sites = {"central": {}, "remote_fra": {}}  # noqa: SLF001
    conn._mc_dead = set()  # noqa: SLF001
    monkeypatch.setattr(conn, "_query_with_site", _rows_from([("remote_fra", _host_row("h"))]))
    asyncio.run(_tree(*primed))
    conn._mc_dead = {"remote_fra"}  # noqa: SLF001
    monkeypatch.setattr(conn, "_query_with_site", _rows_from([]))
    tree = asyncio.run(_tree(*asked))
    assert tree.dead_sites == ["remote_fra"]
    return _staleness(tree)[1]


_OPS = FolderScope(see_all=False, groups=frozenset({"ops"}))


def test_the_same_request_gets_the_rows_of_a_dead_site(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = _tcp_connection(monkeypatch)
    assert _stale_after_remote_died(
        conn, monkeypatch, primed=(_OPS, False), asked=(_OPS, False)
    ) == {"h"}


@pytest.mark.parametrize(
    "asked",
    [
        pytest.param((_OPS, True), id="hard states"),
        pytest.param((FolderScope(see_all=False, groups=frozenset({"dev"})), False), id="groups"),
    ],
)
def test_another_request_gets_no_rows_of_a_dead_site(
    monkeypatch: pytest.MonkeyPatch, asked: tuple[FolderScope | None, bool]
) -> None:
    conn = _tcp_connection(monkeypatch)
    assert _stale_after_remote_died(conn, monkeypatch, primed=(_OPS, False), asked=asked) == set()


def test_rows_of_a_site_dead_for_long_are_not_shown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(livestatus, "_FOLDER_TREE_REPLAY_FOR", -1.0)
    conn = _tcp_connection(monkeypatch)
    assert (
        _stale_after_remote_died(conn, monkeypatch, primed=(_OPS, False), asked=(_OPS, False))
        == set()
    )


def test_a_dead_site_keeps_its_rows_while_more_requests_come_than_are_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _tcp_connection(monkeypatch)
    live = [f"site{i}" for i in range(100)]

    async def _tree(folder_scope: FolderScope) -> FolderTreeData:
        async with conn.with_folder_scope(folder_scope):
            return await conn.get_folder_tree()

    async def _trees_of_other_requests() -> None:
        for i in range(livestatus._FOLDER_TREE_ROWS_KEPT // len(live) + 1):  # noqa: SLF001
            await _tree(FolderScope(see_all=False, groups=frozenset({f"group{i}"})))

    conn._sites = dict.fromkeys(["remote_fra", *live], {})  # noqa: SLF001
    conn._mc_dead = set()  # noqa: SLF001
    monkeypatch.setattr(conn, "_query_with_site", _rows_from([("remote_fra", _host_row("h"))]))
    asyncio.run(_tree(_OPS))
    conn._mc_dead = {"remote_fra"}  # noqa: SLF001
    monkeypatch.setattr(
        conn,
        "_query_with_site",
        _rows_from([(site, _host_row(f"host-{site}")) for site in live]),
    )
    asyncio.run(_trees_of_other_requests())

    assert _staleness(asyncio.run(_tree(_OPS)))[1] == {"h"}


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


def test_folder_tree_shows_a_host_never_checked_as_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _tcp_connection(monkeypatch)
    monkeypatch.setattr(
        conn,
        "_query_with_site",
        _rows_from(
            [("central", _host_row("new-h", checked=False)), ("central", _host_row("up-h"))]
        ),
    )

    tree = asyncio.run(conn.get_folder_tree())

    assert {h["host_name"]: h["state"] for h in tree.hosts} == {"new-h": "PENDING", "up-h": "UP"}


def test_geo_hosts_are_asked_for_once_per_user_within_a_tick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _tcp_connection(monkeypatch)
    queries: list[str] = []

    async def _query(query: str) -> list[list[object]]:
        queries.append(query)
        return [["muc", "Munich", {"maps_lat": "48.1", "maps_lng": "11.6"}, [], []]]

    monkeypatch.setattr(conn, "_query", _query)

    async def _as(auth_user: str | None) -> list[str]:
        token = livestatus._scope_ctx.set(MonitoringScope(auth_user))  # noqa: SLF001
        try:
            return [h["name"] for h in await conn.get_hosts_with_geo()]
        finally:
            livestatus._scope_ctx.reset(token)  # noqa: SLF001

    async def _ticks() -> list[list[str]]:
        return [await _as("alice"), await _as("alice"), await _as("bob")]

    assert asyncio.run(_ticks()) == [["muc"], ["muc"], ["muc"]]
    assert len(queries) == 2


class _FakeSite:
    """A Livestatus that answers with one host, and refuses a query naming an *unknown* column."""

    def __init__(self, host: str, unknown: tuple[bytes, ...] = (b"nme",)) -> None:
        self._host = host
        self._unknown = unknown
        self.queries: list[bytes] = []
        self._server = socket.create_server(("127.0.0.1", 0))
        self.port = self._server.getsockname()[1]
        self.url = f"tcp:127.0.0.1:{self.port}"
        threading.Thread(target=self._serve, daemon=True).start()

    def close(self) -> None:
        self._server.close()

    def _serve(self) -> None:
        while True:
            try:
                client, _ = self._server.accept()
            except OSError:
                return
            threading.Thread(target=self._answer, args=(client,), daemon=True).start()

    def _answer(self, client: socket.socket) -> None:
        with client:
            pending = b""
            while chunk := client.recv(4096):
                pending += chunk
                while b"\n\n" in pending:
                    query, pending = pending.split(b"\n\n", 1)
                    self.queries.append(query)
                    if any(column in query for column in self._unknown):
                        code, body = "400", "unknown column"
                    else:
                        code, body = "200", repr([[self._host]])
                    client.sendall(f"{code} {len(body):>11}\n{body}".encode())


@pytest.fixture(name="sites")
def fixture_sites() -> Iterator[dict[str, _FakeSite]]:
    # Only the remote one lacks ``new_column``, as an older version would.
    sites = {
        "central": _FakeSite("central-h"),
        "remote": _FakeSite("remote-h", (b"nme", b"new_column")),
    }
    yield sites
    for site in sites.values():
        site.close()


@pytest.fixture(name="federated")
def fixture_federated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, sites: dict[str, _FakeSite]
) -> livestatus.LivestatusConnection:
    monkeypatch.setattr(settings, "checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr(checkmk_sites, "sites_mk_mtime", lambda: 1.0)
    monkeypatch.setattr(
        checkmk_sites, "load_sites", lambda: {sid: {"socket": s.url} for sid, s in sites.items()}
    )
    return livestatus.LivestatusConnection(socket_path=_local_socket_path(tmp_path), host=None)


def test_a_query_every_site_refuses_fails_and_keeps_the_sites(
    federated: livestatus.LivestatusConnection,
) -> None:
    with pytest.raises(MKLivestatusQueryError):
        federated._run_multisite_sync("GET hosts\nColumns: name\nFilter: nme = a\n")  # noqa: SLF001

    assert federated.dead_sites() == []
    assert sorted(federated._run_multisite_sync("GET hosts\nColumns: name\n")) == [  # noqa: SLF001
        ["central", "central-h"],
        ["remote", "remote-h"],
    ]


def test_a_site_alone_refusing_a_query_drops_out(
    federated: livestatus.LivestatusConnection,
) -> None:
    rows = federated._run_multisite_sync("GET hosts\nColumns: name\nFilter: new_column = a\n")  # noqa: SLF001

    assert rows == [["central", "central-h"]]
    assert federated.dead_sites() == ["remote"]


def _hosts_as(
    federated: livestatus.LivestatusConnection, scope: MonitoringScope
) -> list[list[object]]:
    token = livestatus._scope_ctx.set(scope)  # noqa: SLF001
    try:
        return sorted(federated._run_multisite_sync("GET hosts\nColumns: name\n"))  # noqa: SLF001
    finally:
        livestatus._scope_ctx.reset(token)  # noqa: SLF001


@pytest.mark.parametrize(
    "monitored, rows",
    [
        pytest.param(None, [["central", "central-h"], ["remote", "remote-h"]], id="all sites"),
        pytest.param(frozenset({"remote"}), [["remote", "remote-h"]], id="one site"),
        pytest.param(frozenset({"gone"}), [], id="no configured site"),
        pytest.param(frozenset(), [], id="no site"),
    ],
)
def test_a_user_sees_the_rows_of_their_monitored_sites(
    federated: livestatus.LivestatusConnection,
    sites: dict[str, _FakeSite],
    monitored: frozenset[str] | None,
    rows: list[list[str]],
) -> None:
    assert _hosts_as(federated, MonitoringScope("alice", monitored)) == rows
    asked = {sid for sid, site in sites.items() if any(b"GET hosts" in q for q in site.queries)}
    assert asked == {row[0] for row in rows}


def test_a_dead_site_the_user_may_not_see_is_not_named(
    federated: livestatus.LivestatusConnection,
) -> None:
    federated._run_multisite_sync("GET hosts\nColumns: name\nFilter: new_column = a\n")  # noqa: SLF001

    async def _dead_as(scope: MonitoringScope) -> list[str]:
        async with federated.with_monitoring_scope(scope):
            return federated.dead_sites()

    assert asyncio.run(_dead_as(MonitoringScope("alice", frozenset({"central"})))) == []
    assert asyncio.run(_dead_as(MonitoringScope("alice"))) == ["remote"]


def _ask_refused_as(federated: livestatus.LivestatusConnection, *auth_users: str) -> None:
    async def _ask() -> None:
        for auth_user in auth_users:
            async with federated.with_monitoring_scope(MonitoringScope(auth_user)):
                with pytest.raises(QueryRefusedError):
                    await federated.get_dyngroup_state("host", "Filter: nme = a\n")

    asyncio.run(_ask())


def _refused_asked(sites: dict[str, _FakeSite]) -> dict[str, int]:
    return {sid: sum(b"nme" in q for q in site.queries) for sid, site in sites.items()}


def test_a_query_every_site_refused_is_not_sent_again_at_once(
    federated: livestatus.LivestatusConnection, sites: dict[str, _FakeSite]
) -> None:
    _ask_refused_as(federated, "alice", "alice")

    assert _refused_asked(sites) == {"central": 1, "remote": 1}


def test_a_refused_query_is_sent_again_after_the_retry_interval(
    monkeypatch: pytest.MonkeyPatch,
    federated: livestatus.LivestatusConnection,
    sites: dict[str, _FakeSite],
) -> None:
    monkeypatch.setattr(livestatus.LivestatusConnection, "_MC_DEAD_RETRY_SECONDS", 0.0)

    _ask_refused_as(federated, "alice", "alice")

    assert _refused_asked(sites) == {"central": 2, "remote": 2}


def test_a_query_refused_for_one_user_is_still_sent_for_another(
    federated: livestatus.LivestatusConnection, sites: dict[str, _FakeSite]
) -> None:
    _ask_refused_as(federated, "alice", "bob")

    assert _refused_asked(sites) == {"central": 2, "remote": 2}


def test_a_refused_query_is_warned_about_once(
    monkeypatch: pytest.MonkeyPatch,
    federated: livestatus.LivestatusConnection,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(livestatus.LivestatusConnection, "_MC_DEAD_RETRY_SECONDS", 0.0)

    with caplog.at_level(logging.WARNING):
        _ask_refused_as(federated, "alice", "alice")

    assert len(caplog.records) == 1
    assert caplog.records[0].getMessage().startswith("Livestatus refused a query")


def test_a_long_refused_query_is_logged_shortened(
    federated: livestatus.LivestatusConnection,
    caplog: pytest.LogCaptureFixture,
) -> None:
    object_filter = "Filter: nme = a\n" + "Filter: name = padding\nOr: 2\n" * 2000

    async def _ask() -> None:
        async with federated.with_monitoring_scope(MonitoringScope("alice")):
            with pytest.raises(QueryRefusedError):
                await federated.get_dyngroup_state("host", object_filter)

    with caplog.at_level(logging.WARNING):
        asyncio.run(_ask())

    message = caplog.records[0].getMessage()
    assert len(message) < len(object_filter) // 10
    assert message.endswith(" characters)")


def test_a_query_a_single_site_refuses_fails_as_refused(
    sites: dict[str, _FakeSite],
) -> None:
    single = livestatus.LivestatusConnection(
        host="127.0.0.1", port=sites["central"].port, tls=False
    )

    with pytest.raises(QueryRefusedError):
        asyncio.run(single.get_dyngroup_state("host", "Filter: nme = a\n"))
