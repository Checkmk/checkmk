#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Backend configuration persistence and runtime registration."""

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from cmk.maps.backend.connections.base import topology_problem_rank
from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations import checkmk_globals
from cmk.maps.backend.schemas.connection import ConnectionConfig
from cmk.maps.backend.services import connection_forms, state_service
from cmk.maps.backend.services.state_service import register_connection as _register

if TYPE_CHECKING:
    from cmk.maps.backend.connections.base import ConnectionBase

logger = logging.getLogger(__name__)


def _local_connection() -> ConnectionConfig:
    """A built-in connection to the site's own Livestatus socket.

    Used when ``maps_connections`` holds no connection: the GUI's factory default
    describes the same connection but is never written to the file this daemon
    reads.
    """
    return ConnectionConfig(
        id=f"cmk_{settings.checkmk_site}",
        type="livestatus",
        label=f"Checkmk {settings.checkmk_site}",
        socket_path=str(Path(settings.checkmk_omd_root) / "tmp" / "run" / "live"),
        checkmk_url=f"/{settings.checkmk_site}",
        port=6557,
        timeout=settings.connection_query_timeout,
    )


def _configured() -> object:
    return checkmk_globals.load_maps_globals().get(checkmk_globals.VAR_CONNECTIONS)


def _effective(raw: object) -> list[ConnectionConfig]:
    """Effective connections of the WATO ``maps_connections`` global.

    WATO is the sole editor; the daemon never writes connections. Falls back to a
    built-in local-site connection when none are configured.
    """
    configs = connection_forms.connections_from_global(raw)
    return configs if configs else [_local_connection()]


def load_all() -> list[ConnectionConfig]:
    """Effective connections, read read-only from the WATO ``maps_connections`` global."""
    return _effective(_configured())


class _Registered:
    """The connections registered with the state service, as last configured."""

    def __init__(self, *, check_every: float = 1.0) -> None:
        # The configured value they were built from. Held, so its identity is not
        # reused: the globals loader returns the same object until a file changed.
        self._raw: object = object()
        self._configs: dict[str, ConnectionConfig] = {}
        # Every connection lookup asks; the files are looked at once per interval.
        self._check_every = check_every
        self._checked = float("-inf")

    def sync(self) -> None:
        """Register what changed since the last call: build new and changed
        connections, close and drop removed ones."""
        now = time.monotonic()
        if now - self._checked < self._check_every:
            return
        self._checked = now
        raw = _configured()
        if raw is self._raw:
            return
        self._raw = raw
        wanted = {cfg.id: cfg for cfg in _effective(raw)}
        for cid in self._configs.keys() - wanted.keys():
            _close(cid)
            state_service.unregister_connection(cid)
            logger.info("Removed connection '%(id)s'", {"id": cid})
        for cid, cfg in wanted.items():
            if self._configs.get(cid) == cfg:
                continue
            _close(cid)
            try:
                _activate(cfg)
            except Exception:
                state_service.unregister_connection(cid)
                logger.exception("Failed to activate connection '%(id)s'", {"id": cid})
                continue
            logger.info(
                "Activated connection '%(id)s' (type=%(type)s)", {"id": cid, "type": cfg.type}
            )
        self._configs = wanted


def _close(connection_id: str) -> None:
    if (connection := state_service.get_registered_connection(connection_id)) is not None:
        connection.close()


_registered = _Registered()


def activate_all() -> None:
    """Register the configured connections, and again whenever they change."""
    _registered.sync()
    state_service.follow_configuration(_registered.sync)


def build_instance(cfg: ConnectionConfig) -> ConnectionBase:
    """Build a connection instance without registering it (e.g. for connection tests)."""
    from cmk.maps.backend.connections.livestatus import LivestatusConnection

    return LivestatusConnection(
        socket_path=cfg.socket_path or "/var/run/nagios/rw/live",
        host=cfg.host,
        port=cfg.port if cfg.port is not None else 6557,
        tls=cfg.tls,
        tls_verify=cfg.tls_verify,
        timeout=cfg.timeout,
        checkmk_url=cfg.checkmk_url,
        automation_user=cfg.automation_user,
        automation_secret=cfg.automation_secret,
    )


def _activate(cfg: ConnectionConfig) -> None:
    """Instantiate and register a connection with the state service."""
    _register(cfg.id, build_instance(cfg))


async def _warmup_tick() -> None:
    """One pass: pre-fetch topology + the top-K bulk-services slice per connection.

    Uses the same ranking as the REST endpoint so warmup primes services for
    exactly the hosts a flow-map page will request — otherwise the warm
    pool only helps the cheap query and the user still pays for the bulk
    services round-trip.
    """
    top_k = settings.flow_map_top_affected_hosts
    for connection_id in state_service.list_connection_ids():
        connection = state_service.get_connection(connection_id)
        if connection is None:
            continue
        try:
            t0 = time.monotonic()
            rows = await connection.get_topology()
            if rows and top_k > 0:
                ranked = sorted(rows, key=topology_problem_rank, reverse=True)
                sample = [r["name"] for r in ranked[:top_k]]
                await connection.get_hosts_services_batch(sample)
            logger.debug(
                "warmup tick connection=%(connection_id)s hosts=%(hosts)d elapsed=%(elapsed).0fms",
                {
                    "connection_id": connection_id,
                    "hosts": len(rows),
                    "elapsed": (time.monotonic() - t0) * 1000,
                },
            )
        except Exception:
            # Stale sockets heal on the next tick; never crash the loop.
            logger.warning(
                "warmup tick failed for connection %(connection_id)s",
                {"connection_id": connection_id},
                exc_info=True,
            )


async def warmup_loop() -> None:
    """Periodically warm livestatus pools so the first user-facing query is fast.

    Idle pools on large sites can take 10-15 s on the first /topology call
    (socket open + cold service-cache fetch). Issuing a small query every
    ``connection_warmup_interval`` seconds keeps the pool primed. Sequential
    `await` per tick rules out overlapping ticks even on slow sites.
    """
    interval = settings.connection_warmup_interval
    if interval <= 0:
        return
    # Prime immediately so the first request after startup is warm.
    await _warmup_tick()
    while True:
        await asyncio.sleep(interval)
        await _warmup_tick()
