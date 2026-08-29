#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Two ways to put a fleet of fake remote sites in front of a central site.

:func:`patched_remotes` replaces the Livestatus client's socket, so the GUI runs in the test
process and talks to :mod:`livestatus_fake` through the real protocol code - real query
building, real response parsing, real multi-site merging - without a site, a port or a root
password. That is what makes a fifty-remote scenario something a laptop can run.

:func:`serve_remotes` is the same responder behind real TCP sockets, for a real OMD site whose
``sites.mk`` points at them. Nothing in the central site can tell the difference: a Livestatus
connection that carries no configuration replication is an ordinary status-only connection, and
that is exactly what a monitoring page reads.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import closing, contextmanager
from dataclasses import dataclass
from typing import override
from unittest import mock

from cmk.ccc.site import SiteId

from .livestatus_fake import EstateShape, FakeSite, FakeVersion, QueryLog

#: The fixed16 response header the client expects in front of every payload.
_RESPONSE_HEADER = "{code:<3} {length:>11}\n"


def response_frame(payload: bytes, code: int = 200) -> bytes:
    return _RESPONSE_HEADER.format(code=code, length=len(payload)).encode("ascii") + payload


def build_sites(
    *,
    central_site_id: str,
    remote_count: int,
    shape: EstateShape,
    version: FakeVersion,
    log: QueryLog,
    latency: float = 0.0,
    central_shape: EstateShape | None = None,
) -> dict[str, FakeSite]:
    """The central site plus ``remote_count`` remotes, all answered by the fake.

    The central site is faked too. Its own core is no more relevant to the comparison than a
    remote's, and faking it keeps every site in the fleet identical, so a scaling curve measures
    the number of sites rather than which one happened to be real.
    """
    sites = {
        central_site_id: FakeSite(
            central_site_id,
            central_shape if central_shape is not None else shape,
            version=version,
            log=log,
            latency=latency,
        )
    }
    for index in range(remote_count):
        site_id = f"remote{index:02d}"
        sites[site_id] = FakeSite(site_id, shape, version=version, log=log, latency=latency)
    return sites


class _FakeSocket:
    """A socket that answers out of a :class:`FakeSite` instead of a network.

    The client writes a query with ``sendall`` and then reads the framed response with ``recv``,
    so everything the client does with the bytes - the fixed16 header, the payload decode, the
    literal parse - is the real code path.
    """

    def __init__(self, site: FakeSite) -> None:
        self._site = site
        self._pending = b""
        #: When the answer currently buffered would have arrived over this site's link. The
        #: wait happens on the read rather than on the write, which is what makes a fan-out
        #: cost one link's latency: the connection sends every site's query first and only then
        #: starts reading, so by the time it reads, every link has been waiting in parallel.
        self._ready_at = 0.0
        # The client's ``receive_data`` uses select/poll on the descriptor, so it needs a real
        # one that is always readable. No data ever travels through it.
        self._write_end, self._read_end = socket.socketpair()
        self._write_end.send(b"x")

    def settimeout(self, timeout: float | None) -> None:
        pass

    def connect(self, address: object) -> None:
        pass

    def fileno(self) -> int:
        return self._read_end.fileno()

    def close(self) -> None:
        self._write_end.close()
        self._read_end.close()

    def recv(self, length: int) -> bytes:
        if (remaining := self._ready_at - time.monotonic()) > 0:
            time.sleep(remaining)
        chunk, self._pending = self._pending[:length], self._pending[length:]
        return chunk

    def send(self, data: bytes) -> None:
        self.sendall(data)

    def sendall(self, data: bytes) -> None:
        self._pending += response_frame(self._site.respond(data.decode("utf-8").strip()))
        self._ready_at = time.monotonic() + self._site.latency


@contextmanager
def patched_remotes(sites: Mapping[str, FakeSite]) -> Iterator[None]:
    """Make every Livestatus connection in this process answer out of ``sites``."""
    sockets: list[_FakeSocket] = []

    # Assigned onto the class, so it is called as a method and receives the connection as its
    # first argument. Getting that wrong makes every site fail to connect and be dropped, which
    # is invisible: the queries still run, against nothing, and every page comes back empty.
    def create_socket(
        connection: object,  # noqa: ARG001
        family: object,  # noqa: ARG001
        site_name: SiteId | None = None,
    ) -> _FakeSocket:
        if site_name is None or str(site_name) not in sites:
            raise AssertionError(
                f"Livestatus connection to unknown site {site_name!r}; "
                f"the fake fleet is {sorted(sites)}"
            )
        created = _FakeSocket(sites[str(site_name)])
        sockets.append(created)
        return created

    try:
        with mock.patch(
            "cmk.livestatus_client.SingleSiteConnection._create_socket", new=create_socket
        ):
            yield
    finally:
        for created in sockets:
            created.close()


# .
#   .--tcp------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class ServedFleet:
    """Where a fleet of TCP-served fake sites can be reached."""

    ports: Mapping[str, int]

    def socket_spec(self, site_id: str) -> tuple[str, dict[str, object]]:
        """The ``socket`` entry a central site's ``sites.mk`` needs for this fake site."""
        return (
            "tcp",
            {"address": ("127.0.0.1", self.ports[site_id]), "tls": ("plain_text", {})},
        )


class _RemoteServer(threading.Thread):
    """One listening socket answering Livestatus queries for one fake site.

    Livestatus keeps connections alive, so a client sends many queries down one socket. Each
    connection therefore gets its own thread that loops until the peer goes away.
    """

    def __init__(self, site: FakeSite) -> None:
        super().__init__(name=f"fake-livestatus-{site.site_id}", daemon=True)
        self._site = site
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(64)
        self._stopping = threading.Event()

    @property
    def port(self) -> int:
        return int(self._listener.getsockname()[1])

    @override
    def run(self) -> None:
        while not self._stopping.is_set():
            try:
                connection, _peer = self._listener.accept()
            except OSError:
                return
            threading.Thread(
                target=self._serve, args=(connection,), daemon=True, name=self.name
            ).start()

    def _serve(self, connection: socket.socket) -> None:
        with closing(connection):
            buffered = b""
            while not self._stopping.is_set():
                try:
                    chunk = connection.recv(65536)
                except OSError:
                    return
                if not chunk:
                    return
                buffered += chunk
                # A query ends at the blank line the client appends after the headers.
                while b"\n\n" in buffered:
                    query, _, buffered = buffered.partition(b"\n\n")
                    try:
                        payload = self._site.respond(query.decode("utf-8"))
                        # Served from its own thread, so sleeping here delays this site alone -
                        # a fan-out still costs one link's latency, as over a real network.
                        if self._site.latency:
                            time.sleep(self._site.latency)
                        frame = response_frame(payload)
                    except Exception as exc:
                        frame = response_frame(str(exc).encode("utf-8"), code=400)
                    try:
                        connection.sendall(frame)
                    except OSError:
                        return

    def stop(self) -> None:
        self._stopping.set()
        self._listener.close()


@contextmanager
def serve_remotes(sites: Sequence[FakeSite]) -> Iterator[ServedFleet]:
    """Serve every given fake site on its own loopback port for the duration of the block."""
    servers = [_RemoteServer(site) for site in sites]
    try:
        for server in servers:
            server.start()
        yield ServedFleet(ports={site.site_id: server.port for site, server in zip(sites, servers)})
    finally:
        for server in servers:
            server.stop()
