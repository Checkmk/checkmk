#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Livestatus connection via Checkmk's ``cmk.livestatus_client``."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import re
import threading
import time
from collections.abc import AsyncIterator, Iterable, Mapping
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, UTC
from pathlib import Path
from typing import cast, Literal, override, TYPE_CHECKING

if TYPE_CHECKING:
    from cmk.livestatus_client import (
        MultiSiteConnection,
        Query,
        SingleSiteConnection,
        SiteConfiguration,
    )

import httpx

from cmk.ccc.site import SiteId
from cmk.livestatus_client import lqencode
from cmk.maps.backend.connections.base import (
    ConnectionBase,
    FolderInfo,
    FolderTreeData,
    FolderTreeHostRow,
    GeoHost,
    MetricHistoryResult,
    ServiceMatchRow,
    ServiceRow,
    TopologyRow,
)
from cmk.maps.backend.core.config import settings
from cmk.maps.backend.core.ttl_cache import TtlCache
from cmk.maps.backend.integrations import checkmk_folders as _cmk_folders
from cmk.maps.backend.integrations import checkmk_sites as _cmk_sites
from cmk.maps.backend.integrations.checkmk import FolderScope
from cmk.maps.backend.schemas.state import (
    CommentInfo,
    DowntimeInfo,
    ObjectDetails,
    ObjectState,
    ServicesSummary,
)
from cmk.maps.shared.autocomplete import object_autocomplete_query, unique_names
from cmk.maps.shared.geo import LAT_LABEL, LAT_VAR, LNG_LABEL, LNG_VAR, resolve_host_coords
from cmk.maps.shared.perfdata import parse_perf_metrics
from cmk.maps.shared.rows import (
    row_bool,
    row_dict,
    row_float,
    row_float_or_none,
    row_int,
    row_list,
    row_str,
    row_strs,
)
from cmk.maps.shared.states import (
    HOST_STATE_MAP,
    SERVICE_STATE_MAP,
    SEVERITY_RANK,
    severity_rank,
)
from cmk.utils.misc import pnp_cleanup

logger = logging.getLogger(__name__)


# When set, every Livestatus query in the current asyncio task includes
# ``AuthUser: <username>`` so Livestatus only returns objects the user
# is a contact for (contact-group filtering).
_auth_user_ctx: ContextVar[str | None] = ContextVar("_auth_user_ctx", default=None)

# The requesting user's SETUP-folder read visibility, used by ``get_folder_tree``
# to mark which (otherwise unscoped) folders the user may see. Distinct from
# ``_auth_user_ctx``: a see-all guest scopes folders by contact group yet has no
# Livestatus AuthUser. ``None`` means unrestricted (not set).
_folder_scope_ctx: ContextVar[FolderScope | None] = ContextVar("_folder_scope_ctx", default=None)


def _default_site_id(sid: str | None = None) -> str:
    """Resolve a row's site id, falling back to the configured default site.

    ``sid`` is the per-row site tag from a multisite query (``None`` on
    single-site connections, where :meth:`_query_with_site` yields no tag).
    An empty/``None`` tag falls back to the configured ``checkmk_site``, then
    to ``"local"`` as a last resort. Centralised here so every state /
    command path resolves the site the same way.
    """
    return sid or settings.checkmk_site or "local"


# A Livestatus row is a heterogeneous JSON array: each column can hold a scalar,
# a list, or an object. We treat it as list[object] and use the shared row_*
# helpers (cmk.maps.shared.rows) for typed extraction with sensible defaults.
LivestatusRow = list[object]


def _services_summary_from_row(row: LivestatusRow, base: int) -> ServicesSummary:
    """Build ``ServicesSummary`` from 5 consecutive ``num_services_*`` columns
    starting at ``base`` (order: ok, warn, crit, unknown, pending)."""
    return ServicesSummary(
        ok=row_int(row, base),
        warning=row_int(row, base + 1),
        critical=row_int(row, base + 2),
        unknown=row_int(row, base + 3),
        pending=row_int(row, base + 4),
    )


def _worst_state(states: list[str]) -> str:
    """Worst of *states* by the combined severity ladder. Requires non-empty input."""
    return max(states, key=lambda s: SEVERITY_RANK.get(s, 0))


def _host_states_rollup(states: list[str]) -> tuple[str, ServicesSummary]:
    """Worst host state + host-state counts mapped onto the ``services_summary``
    slots so the hover/tooltip renders group counts like host objects:
    UP=ok, DOWN=critical, UNREACHABLE=unknown."""
    return _worst_state(states), ServicesSummary(
        ok=sum(1 for s in states if s == "UP"),
        critical=sum(1 for s in states if s == "DOWN"),
        unknown=sum(1 for s in states if s == "UNREACHABLE"),
        pending=sum(1 for s in states if s == "PENDING"),
    )


def _service_states_rollup(states: list[str]) -> tuple[str, ServicesSummary]:
    """Worst service state + per-slot service-state counts."""
    return _worst_state(states), ServicesSummary(
        ok=sum(1 for s in states if s == "OK"),
        warning=sum(1 for s in states if s == "WARNING"),
        critical=sum(1 for s in states if s == "CRITICAL"),
        unknown=sum(1 for s in states if s == "UNKNOWN"),
        pending=sum(1 for s in states if s == "PENDING"),
    )


def _folder_path_from_filename(filename: str) -> str:
    """WATO ``host.filename`` → normalised folder path.

    ``/wato/datacenters/muc/hosts.mk`` → ``datacenters/muc``; the root folder
    (``/wato/hosts.mk``) and non-WATO/empty filenames → ``""``.
    """
    fn = filename.strip().removeprefix("/").removeprefix("wato/")
    fn = fn.removesuffix("hosts.mk")
    return fn.strip("/")


# The real SETUP structure (incl. empty folders), titles and
# effective read-permitted contact groups come from the GUI-prepared skeleton
# (``maps.d/wato/folder_perms.mk``, written by cmk.maps.gui._folders via the real
# ``Folder.groups()``), not from Livestatus (which only knows folders that contain
# hosts). Cached on the file mtime — the skeleton changes only on activation, but
# the read would otherwise run on every state tick.
_wato_folders_cache: dict[float, list[FolderInfo]] = {}


def _folder_info_from_entry(entry: dict[str, object]) -> FolderInfo | None:
    """Convert one prepared-skeleton entry into a ``FolderInfo``.

    The root folder carries ``path == ""``; ``permitted_groups`` is the effective
    read permission the GUI already resolved. Drops entries missing the required
    ``path``/``title``.
    """
    path = entry.get("path")
    title = entry.get("title")
    if not isinstance(path, str) or not isinstance(title, str):
        return None
    raw_groups = entry.get("permitted_groups", [])
    info: FolderInfo = {
        "path": path,
        "title": title,
        "permitted_groups": (
            [g for g in raw_groups if isinstance(g, str)] if isinstance(raw_groups, list) else []
        ),
    }
    fid = entry.get("folder_id")
    if isinstance(fid, str) and fid:
        info["folder_id"] = fid
    return info


async def _load_wato_folders() -> list[FolderInfo]:
    """Cached, off-event-loop read of the GUI-prepared SETUP-folder skeleton."""
    mtime = _cmk_folders.folder_perms_mtime()
    cached = _wato_folders_cache.get(mtime)
    if cached is not None:
        return cached
    raw = await asyncio.to_thread(_cmk_folders.load_folder_perms)
    folders = [info for entry in raw if (info := _folder_info_from_entry(entry)) is not None]
    logger.debug(
        "Folder-tree: loaded %(folder_count)d prepared WATO folders",
        {"folder_count": len(folders)},
    )
    # Single-entry cache keyed by mtime: a new activation bumps the mtime and
    # invalidates the previous skeleton.
    _wato_folders_cache.clear()
    _wato_folders_cache[mtime] = folders
    return folders


# State-code maps + severity ranking are the shared GUI↔daemon vocabulary
# (cmk.maps.shared.states); worst-state roll-ups use the one combined SEVERITY_RANK.
_STATE_TYPE_MAP = {0: "SOFT", 1: "HARD"}

_HOST_EXTRA_COLS = (
    "address alias last_check next_check state_type current_attempt max_check_attempts"
    " last_state_change notifications_enabled active_checks_enabled check_command"
)
_SVC_EXTRA_COLS = (
    "last_check next_check state_type current_attempt max_check_attempts last_state_change"
    " notifications_enabled active_checks_enabled check_command"
)

# Column lists for the on-demand object-details endpoint. Order matters —
# _build_details indexes positionally.
_HOST_DETAIL_COLS = (
    "long_plugin_output check_command latency execution_time is_flapping"
    " in_notification_period notification_period check_interval"
    " parents childs groups contact_groups labels"
)
_SVC_DETAIL_COLS = (
    "long_plugin_output check_command latency execution_time is_flapping"
    " in_notification_period notification_period check_interval"
    " host_groups groups contact_groups labels last_time_ok"
)
_COMMENT_COLS = "id author comment entry_time expire_time"
_DOWNTIME_COLS = "id author comment start_time end_time fixed"


def _apply_extra(
    state: ObjectState, row: LivestatusRow, offset: int = 5, *, include_address: bool = False
) -> ObjectState:
    """Fill the tail ObjectState fields (address, timings, attempt counters) from the row."""
    col = offset
    if include_address:
        state.address = row_str(row, col)
        state.alias = row_str(row, col + 1)
        col += 2
    lc = row_float(row, col)
    nc = row_float(row, col + 1)
    lsc = row_float(row, col + 5)
    state.last_check = lc if lc > 0 else None
    state.next_check = nc if nc > 0 else None
    state.state_type = _STATE_TYPE_MAP.get(row_int(row, col + 2, default=1), "HARD")
    state.current_attempt = row_int(row, col + 3)
    state.max_attempts = row_int(row, col + 4)
    state.last_state_change = lsc if lsc > 0 else None
    state.notifications_enabled = row_bool(row, col + 6, default=True)
    state.active_checks_enabled = row_bool(row, col + 7, default=True)
    state.check_command = row_str(row, col + 8)
    return state


def _is_central_local_socket(host: str | None, socket_path: str) -> bool:
    if host is not None:
        return False
    return socket_path == str(Path(settings.checkmk_omd_root) / "tmp" / "run" / "live")


def _lql_to_query(lql: str) -> Query:
    """Parse bare LQL into a structured ``Query`` for the cmk client.

    Only structured queries (``QuerySpecification``) get ``OutputFormat: json``
    from the client; plain strings are parsed with ``ast.literal_eval``, which
    is ~25x slower on large responses (5k rows: 144ms vs 6ms). Queries with
    blob columns automatically fall back to the python3 format inside the
    client. On anything unexpected (no GET line, repeated Columns) return the
    string query unchanged — correct, just slower.
    """
    from cmk.livestatus_client import Query, QuerySpecification

    # strip("\n"), not strip(): an empty filter value ("Filter: name != \n")
    # carries a meaningful trailing space on the last line.
    lines = lql.strip("\n").splitlines()
    if not lines or not lines[0].startswith("GET "):
        return Query(lql)
    columns: list[str] = []
    headers: list[str] = []
    for line in lines[1:]:
        if line.startswith("Columns:"):
            if columns:
                return Query(lql)
            columns = line.split(":", 1)[1].split()
        else:
            headers.append(line)
    header_str = "\n".join(headers) + "\n" if headers else ""
    return Query(QuerySpecification(lines[0][4:].strip(), columns, header_str))


def _build_state_from_row(
    row: LivestatusRow,
    state_map: dict[int, str],
    type_: str,
    *,
    include_address: bool = False,
    site_id: str | None = None,
) -> ObjectState:
    """Construct an ObjectState from a livestatus row with the standard 5-column prefix."""
    state = ObjectState(
        object_id="",
        type=type_,
        state=state_map.get(row_int(row, 0), "UNKNOWN"),
        output=row_str(row, 1),
        perf_data=row_str(row, 2),
        acknowledged=row_bool(row, 3, default=False),
        in_downtime=row_int(row, 4) > 0,
        site_id=site_id,
    )
    return _apply_extra(state, row, include_address=include_address)


def _parse_host_state_row(
    row: LivestatusRow, *, site_id: str | None = None
) -> tuple[str, ObjectState]:
    """Parse host row [name, state, output, perf_data, ack, downtime, ...extra]."""
    state = ObjectState(
        object_id="",
        type="host",
        state=HOST_STATE_MAP.get(row_int(row, 1), "UNKNOWN"),
        output=row_str(row, 2),
        perf_data=row_str(row, 3),
        acknowledged=row_bool(row, 4, default=False),
        in_downtime=row_int(row, 5) > 0,
        site_id=site_id,
    )
    return row_str(row, 0), _apply_extra(state, row, offset=6, include_address=True)


def _parse_service_state_row(
    row: LivestatusRow, *, site_id: str | None = None
) -> tuple[tuple[str, str], ObjectState]:
    """Parse service row [host_name, description, state, output, perf_data, ack, downtime, ...extra]."""
    state = ObjectState(
        object_id="",
        type="service",
        state=SERVICE_STATE_MAP.get(row_int(row, 2), "UNKNOWN"),
        output=row_str(row, 3),
        perf_data=row_str(row, 4),
        acknowledged=row_bool(row, 5, default=False),
        in_downtime=row_int(row, 6) > 0,
        site_id=site_id,
    )
    return (row_str(row, 0), row_str(row, 1)), _apply_extra(state, row, offset=7)


def _worst_state_dict[StateKey](
    pairs: Iterable[tuple[StateKey, ObjectState]],
) -> dict[StateKey, ObjectState]:
    """Fold ``(key, state)`` pairs into a dict, keeping the WORST state per key.

    In a distributed setup two sites can expose the same host/service name; the
    rows arrive concatenated. A plain ``dict(...)`` would let the last row win
    and silently drop a CRITICAL from another site. Keep the most severe so a
    real problem is never hidden (a real state also beats a PENDING placeholder).
    """
    merged: dict[StateKey, ObjectState] = {}
    for key, state in pairs:
        existing = merged.get(key)
        if existing is None or severity_rank(state.state) > severity_rank(existing.state):
            merged[key] = state
    return merged


def _build_details(
    type_: Literal["host", "service"],
    host: str,
    service: str | None,
    row: LivestatusRow,
    comment_rows: list[LivestatusRow],
    downtime_rows: list[LivestatusRow],
) -> ObjectDetails:
    """Map a host/service detail row + comments/downtimes onto ObjectDetails.

    Column order must mirror ``_HOST_DETAIL_COLS`` / ``_SVC_DETAIL_COLS``.
    The leading 9 columns are common; the trailing group list differs (host:
    parents, children, groups · service: host_groups, groups + last_time_ok).
    """
    common_count = 8
    d = ObjectDetails(
        type=type_,
        host_name=host,
        service_description=service,
        # Livestatus encodes line breaks in the agent output as the literal "\n"
        # so they survive the line-based wire protocol; the UI wants real newlines.
        long_output=row_str(row, 0).replace("\\n", "\n").replace("\\r", ""),
        check_command=row_str(row, 1),
        latency=row_float_or_none(row, 2),
        execution_time=row_float_or_none(row, 3),
        is_flapping=row_bool(row, 4, default=False),
        in_notification_period=row_bool(row, 5, default=True),
        notification_period=row_str(row, 6),
        check_interval=row_float_or_none(row, 7),
    )

    if type_ == "host":
        d.parents = row_strs(row, common_count)
        d.children = row_strs(row, common_count + 1)
        d.host_groups = row_strs(row, common_count + 2)
        d.contact_groups = row_strs(row, common_count + 3)
        d.labels = {str(k): str(v) for k, v in row_dict(row, common_count + 4).items()}
    else:
        d.host_groups = row_strs(row, common_count)
        d.service_groups = row_strs(row, common_count + 1)
        d.contact_groups = row_strs(row, common_count + 2)
        d.labels = {str(k): str(v) for k, v in row_dict(row, common_count + 3).items()}
        d.last_time_ok = row_float_or_none(row, common_count + 4)

    d.comments = [
        CommentInfo(
            id=row_int(r, 0),
            author=row_str(r, 1),
            comment=row_str(r, 2),
            entry_time=row_float(r, 3),
            expire_time=row_float_or_none(r, 4),
        )
        for r in comment_rows
    ]
    d.downtimes = [
        DowntimeInfo(
            id=row_int(r, 0),
            author=row_str(r, 1),
            comment=row_str(r, 2),
            start_time=row_float(r, 3),
            end_time=row_float(r, 4),
            fixed=row_bool(r, 5, default=True),
        )
        for r in downtime_rows
    ]
    return d


class LivestatusConnection(ConnectionBase):
    """Connects to a Livestatus socket (Unix or TCP) and queries host/service states."""

    connection_id: str = "live_1"

    def __init__(
        self,
        socket_path: str = "/var/run/nagios/rw/live",
        host: str | None = None,
        port: int = 6557,
        tls: bool = True,
        tls_verify: bool = True,
        timeout: float = 10.0,
        checkmk_url: str | None = None,
        automation_user: str | None = None,
        automation_secret: str | None = None,
    ) -> None:
        # TLS only applies to the TCP path. OMD's `LIVESTATUS_TLS=on` wraps the
        # 6557 listener in stunnel, so the cmk client must speak TLS there;
        # unix-socket connections never do.
        self._use_tls = bool(tls and host)
        self._tls_verify = tls_verify
        self._timeout = timeout
        self._checkmk_url = checkmk_url
        self._automation_user = automation_user
        self._automation_secret = automation_secret
        self._semaphore = asyncio.Semaphore(settings.connection_pool_size)
        # Separate, tighter cap on bulk-services fan-out so 500-host top-K
        # fetches don't blast the unix-socket listen backlog (EAGAIN). Held
        # at chunk granularity in get_hosts_services_batch.
        self._bulk_chunk_semaphore = asyncio.Semaphore(settings.flow_map_bulk_max_concurrent_chunks)
        # Per-site trust: last successful foldertree host rows per
        # (auth-scope, site-filter) -> site_id, replayed when a site dies.
        self._ft_rows_cache: dict[
            tuple[str | None, tuple[str, ...] | None], dict[str, list[FolderTreeHostRow]]
        ] = {}
        # Per-host-set cache for get_services_summary (TTL=_SERVICES_SUMMARY_CACHE_TTL).
        # Keyed by (auth user, host set): the query is auth-scoped, so the cache
        # must be too (mirrors _ft_rows_cache).
        self._services_summary_cache: TtlCache[
            tuple[str | None, frozenset[str]], dict[str, ServicesSummary]
        ] = TtlCache(maxsize=32)

        # Auto-federate when this connection points at the central site's local
        # Livestatus socket — the socket only sees local data, so MultiSiteConnection
        # is required to also reach remote-site hosts/services. Eligibility is
        # fixed by the socket target; whether we actually federate additionally
        # depends on the prepared sitespecs file existing, which may only appear
        # after startup (see _adopt_sites_if_appeared).
        self._federation_eligible = _is_central_local_socket(host, socket_path)
        self._sites: dict[str, dict[str, object]] | None = (
            _cmk_sites.load_sites() if self._federation_eligible else None
        )
        # Last sitespecs mtime seen while still on the single-socket path; lets the
        # absent->present adoption skip re-parsing an unchanged (or absent) file.
        self._single_mode_mtime: float = 0.0
        self._mc: MultiSiteConnection | None = None
        self._mc_mtime: float = 0.0
        # monotonic timestamp of the last MC (re)build — drives the dead-site
        # reconnect retry (see _mc_needs_rebuild).
        self._mc_built_at: float = 0.0
        self._mc_lock = threading.Lock()
        self._mc_dead: set[str] = set()
        if self._sites:
            logger.info(
                "Livestatus federation enabled: %(site_count)d sites (%(sites)s)",
                {
                    "site_count": len(self._sites),
                    "sites": ", ".join(sorted(self._sites)),
                },
            )

        self._ss_socketurl = f"tcp:{host}:{port}" if host else f"unix:{socket_path}"
        # Explicit because the client's verify=True fallback reads $OMD_ROOT
        # from the environment, which Maps does not rely on.
        self._ss_ca_file = str(
            Path(settings.checkmk_omd_root) / "var" / "ssl" / "ca-certificates.crt"
        )
        if self._sites is None:
            logger.info(
                "Livestatus single-site via cmk.livestatus_client (%(socket_url)s)",
                {"socket_url": self._ss_socketurl},
            )

    @asynccontextmanager
    @override
    async def with_auth_user(self, username: str) -> AsyncIterator[None]:
        """Context manager: scope Livestatus queries to *username*'s contact groups.

        While active, every Livestatus query in this asyncio task appends
        ``AuthUser: <username>`` to the LQL request so Livestatus only returns
        hosts/services the user is a contact for.
        """
        token = _auth_user_ctx.set(username)
        try:
            yield
        finally:
            _auth_user_ctx.reset(token)

    @asynccontextmanager
    @override
    async def with_folder_scope(self, scope: FolderScope | None) -> AsyncIterator[None]:
        """Context manager: scope the SETUP folder skeleton (``get_folder_tree``)
        to *scope*'s readable folders. Independent of ``with_auth_user`` because
        folder-read permission and monitoring host visibility differ."""
        token = _folder_scope_ctx.set(scope)
        try:
            yield
        finally:
            _folder_scope_ctx.reset(token)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @override
    async def get_host_state(self, hostname: str) -> ObjectState:
        query = (
            f"GET hosts\n"
            f"Columns: state plugin_output perf_data acknowledged scheduled_downtime_depth {_HOST_EXTRA_COLS}\n"
            f"Filter: name = {lqencode(hostname)}\n"
        )
        tagged = await self._query_with_site(query)
        if not tagged:
            return ObjectState(object_id="", type="host", state="PENDING")
        sid, row = tagged[0]
        return _build_state_from_row(
            row,
            HOST_STATE_MAP,
            "host",
            include_address=True,
            site_id=_default_site_id(sid),
        )

    @override
    async def get_service_state(self, host: str, service: str) -> ObjectState:
        query = (
            f"GET services\n"
            f"Columns: state plugin_output perf_data acknowledged scheduled_downtime_depth {_SVC_EXTRA_COLS}\n"
            f"Filter: host_name = {lqencode(host)}\n"
            f"Filter: description = {lqencode(service)}\n"
        )
        tagged = await self._query_with_site(query)
        if not tagged:
            return ObjectState(object_id="", type="service", state="PENDING")
        sid, row = tagged[0]
        return _build_state_from_row(
            row,
            SERVICE_STATE_MAP,
            "service",
            site_id=_default_site_id(sid),
        )

    async def get_service_perf_and_cmd(self, host: str, service: str) -> tuple[str, str]:
        """Return (perf_data, check_command) for a single service."""
        query = (
            f"GET services\n"
            f"Columns: perf_data check_command\n"
            f"Filter: host_name = {lqencode(host)}\n"
            f"Filter: description = {lqencode(service)}\n"
        )
        rows = await self._query(query)
        if not rows:
            return "", ""
        r = rows[0]
        return row_str(r, 0), row_str(r, 1)

    @override
    async def get_host_details(self, hostname: str) -> ObjectDetails | None:
        return await self._fetch_details("host", hostname, None)

    @override
    async def get_service_details(self, hostname: str, service: str) -> ObjectDetails | None:
        return await self._fetch_details("service", hostname, service)

    async def _fetch_details(
        self, type_: Literal["host", "service"], host: str, service: str | None
    ) -> ObjectDetails | None:
        is_host = type_ == "host"
        now = int(time.time())
        if is_host:
            row_table, row_filter = "hosts", f"Filter: name = {lqencode(host)}\n"
            scope_filter = f"Filter: host_name = {lqencode(host)}\nFilter: is_service = 0\nAnd: 2\n"
        else:
            assert service is not None
            row_table = "services"
            row_filter = (
                f"Filter: host_name = {lqencode(host)}\nFilter: description = {lqencode(service)}\n"
            )
            scope_filter = (
                f"Filter: host_name = {lqencode(host)}\n"
                f"Filter: service_description = {lqencode(service)}\nAnd: 2\n"
            )
        cols = _HOST_DETAIL_COLS if is_host else _SVC_DETAIL_COLS
        # Drop expired comments and ended downtimes — the drawer header reads
        # "Active downtimes", and stale comments add noise without value.
        active_cmt = f"Filter: expire_time = 0\nFilter: expire_time >= {now}\nOr: 2\n"
        active_dt = f"Filter: end_time >= {now}\n"
        rows, cmt_rows, dt_rows = await asyncio.gather(
            self._query(f"GET {row_table}\nColumns: {cols}\n{row_filter}"),
            self._query(f"GET comments\nColumns: {_COMMENT_COLS}\n{scope_filter}{active_cmt}"),
            self._query(f"GET downtimes\nColumns: {_DOWNTIME_COLS}\n{scope_filter}{active_dt}"),
        )
        if not rows:
            return None
        return _build_details(type_, host, service, rows[0], cmt_rows, dt_rows)

    @override
    async def get_host_hard_state(self, hostname: str) -> ObjectState:
        query = (
            f"GET hosts\n"
            f"Columns: last_hard_state plugin_output perf_data acknowledged scheduled_downtime_depth {_HOST_EXTRA_COLS}\n"
            f"Filter: name = {lqencode(hostname)}\n"
        )
        tagged = await self._query_with_site(query)
        if not tagged:
            return ObjectState(object_id="", type="host", state="PENDING")
        sid, row = tagged[0]
        return _build_state_from_row(
            row,
            HOST_STATE_MAP,
            "host",
            include_address=True,
            site_id=_default_site_id(sid),
        )

    @override
    async def get_service_hard_state(self, host: str, service: str) -> ObjectState:
        query = (
            f"GET services\n"
            f"Columns: last_hard_state plugin_output perf_data acknowledged scheduled_downtime_depth {_SVC_EXTRA_COLS}\n"
            f"Filter: host_name = {lqencode(host)}\n"
            f"Filter: description = {lqencode(service)}\n"
        )
        tagged = await self._query_with_site(query)
        if not tagged:
            return ObjectState(object_id="", type="service", state="PENDING")
        sid, row = tagged[0]
        return _build_state_from_row(
            row,
            SERVICE_STATE_MAP,
            "service",
            site_id=_default_site_id(sid),
        )

    @override
    async def get_hostgroup_states(self, group: str) -> ObjectState:
        # Distinguish "group does not exist" (NOT_FOUND) from "group exists but
        # is empty / hosts not yet checked" (PENDING) so the UI can render them
        # differently. Two queries are intentional — `GET hosts ... Filter:
        # groups >=` returns 0 rows for both cases.
        exists_q = f"GET hostgroups\nColumns: name\nFilter: name = {lqencode(group)}\n"
        exists_rows = await self._query(exists_q)
        if not exists_rows:
            return ObjectState(object_id="", type="hostgroup", state="NOT_FOUND")
        query = f"GET hosts\nColumns: state\nFilter: groups >= {lqencode(group)}\n"
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="hostgroup", state="PENDING")
        states = [HOST_STATE_MAP.get(row_int(r, 0), "UNKNOWN") for r in rows]
        worst, summary = _host_states_rollup(states)
        return ObjectState(object_id="", type="hostgroup", state=worst, services_summary=summary)

    @override
    async def get_servicegroup_states(self, group: str) -> ObjectState:
        exists_q = f"GET servicegroups\nColumns: name\nFilter: name = {lqencode(group)}\n"
        exists_rows = await self._query(exists_q)
        if not exists_rows:
            return ObjectState(object_id="", type="servicegroup", state="NOT_FOUND")
        query = f"GET services\nColumns: state\nFilter: groups >= {lqencode(group)}\n"
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="servicegroup", state="PENDING")
        states = [SERVICE_STATE_MAP.get(row_int(r, 0), "UNKNOWN") for r in rows]
        worst, summary = _service_states_rollup(states)
        return ObjectState(object_id="", type="servicegroup", state=worst, services_summary=summary)

    @override
    async def get_dyngroup_state(self, object_types: str, object_filter: str) -> ObjectState:
        # NagVis-style: feed the validated filter into GET hosts/services and
        # aggregate worst-of. normalize_object_filter at the schema layer has
        # already restricted this to safe Filter:/And:/Or: lines.
        lql_filter = object_filter.replace("\\n", "\n")
        if not lql_filter.endswith("\n"):
            lql_filter += "\n"
        if object_types == "service":
            rows = await self._query(f"GET services\nColumns: state\n{lql_filter}")
            if not rows:
                return ObjectState(object_id="", type="dyngroup", state="PENDING")
            states = [SERVICE_STATE_MAP.get(row_int(r, 0), "UNKNOWN") for r in rows]
            worst, summary = _service_states_rollup(states)
            return ObjectState(object_id="", type="dyngroup", state=worst, services_summary=summary)
        # Host dyngroups report two rollups: member host states and their
        # aggregated service states (the O(1) num_services_* counters).
        rows = await self._query(
            "GET hosts\nColumns: state num_services_ok num_services_warn "
            f"num_services_crit num_services_unknown num_services_pending\n{lql_filter}"
        )
        if not rows:
            return ObjectState(object_id="", type="dyngroup", state="PENDING")
        states = [HOST_STATE_MAP.get(row_int(r, 0), "UNKNOWN") for r in rows]
        worst, hosts_summary = _host_states_rollup(states)
        services_summary = ServicesSummary(
            ok=sum(row_int(r, 1) for r in rows),
            warning=sum(row_int(r, 2) for r in rows),
            critical=sum(row_int(r, 3) for r in rows),
            unknown=sum(row_int(r, 4) for r in rows),
            pending=sum(row_int(r, 5) for r in rows),
        )
        return ObjectState(
            object_id="",
            type="dyngroup",
            state=worst,
            services_summary=services_summary,
            hosts_summary=hosts_summary,
        )

    @override
    async def get_objects(
        self, obj_type: str, host: str | None = None, search: str | None = None
    ) -> list[str]:
        # Filtered and hard-capped at the source, so a multi-million-host site
        # never streams every name into the editor — the same approach as
        # cmk.gui's monitored_hostname_autocompleter. The cap is logged when hit
        # so truncation isn't silent.
        limit = settings.object_autocomplete_limit
        query = object_autocomplete_query(
            obj_type, escape=lqencode, limit=limit, host=host, search=search
        )
        if query is None:
            return []
        rows = await self._query(query)
        names = unique_names(row_str(r, 0) for r in rows)
        # The cap is about what the query returned, not what survived the
        # de-duplication — a truncated answer stays worth reporting.
        if len(rows) >= limit:
            logger.info(
                "%(what)s autocomplete truncated to %(limit)d; site has more — type to narrow",
                {"what": obj_type, "limit": limit},
            )
        # MultiSiteConnection applies ``Limit`` per site and concatenates, so a
        # federated result can hold up to limit×num_sites names. Re-slice so the
        # cap the editor relies on holds across a distributed setup too.
        return names[:limit]

    @override
    async def get_group_members(self, group_type: str, group_name: str) -> list[str]:
        if group_type == "all_hosts":
            rows = await self._query("GET hosts\nColumns: name\n")
            return [row_str(r, 0) for r in rows]
        if group_type == "all_services":
            rows = await self._query("GET services\nColumns: host_name description\n")
            return [f"{row_str(r, 0)};{row_str(r, 1)}" for r in rows]
        if group_type == "hostgroup":
            query = f"GET hosts\nColumns: name\nFilter: groups >= {lqencode(group_name)}\n"
            rows = await self._query(query)
            return [row_str(r, 0) for r in rows]
        if group_type == "servicegroup":
            query = f"GET services\nColumns: host_name description\nFilter: groups >= {lqencode(group_name)}\n"
            rows = await self._query(query)
            return [f"{row_str(r, 0)};{row_str(r, 1)}" for r in rows]
        return []

    @override
    async def get_topology(self) -> list[TopologyRow]:
        # The num_services_* columns are O(1) on the hosts table (the core
        # maintains them), so the donut summary comes for free in this single
        # query — no separate Stats round-trip, and multisite-safe because each
        # row is self-contained per host.
        tagged = await self._query_with_site(
            "GET hosts\n"
            "Columns: name parents state plugin_output "
            "alias address acknowledged scheduled_downtime_depth last_check next_check "
            "state_type current_attempt max_check_attempts last_state_change "
            "notifications_enabled active_checks_enabled "
            "num_services_ok num_services_warn num_services_crit "
            "num_services_unknown num_services_pending\n"
        )
        result: list[TopologyRow] = []
        for site_id, r in tagged:
            name = row_str(r, 0)
            if not name:
                continue
            raw_parents = r[1] if len(r) > 1 else ""
            if isinstance(raw_parents, list):
                parents = [p for p in raw_parents if isinstance(p, str) and p]
            elif isinstance(raw_parents, str):
                parents = [p.strip() for p in raw_parents.split(",") if p.strip()]
            else:
                parents = []
            lc = row_float(r, 8)
            nc = row_float(r, 9)
            lsc = row_float(r, 13)
            row: TopologyRow = {
                "name": name,
                "parents": parents,
                "state": HOST_STATE_MAP.get(row_int(r, 2), "UNKNOWN"),
                "output": row_str(r, 3),
                "alias": row_str(r, 4),
                "address": row_str(r, 5),
                "acknowledged": row_bool(r, 6, default=False),
                "in_downtime": row_int(r, 7) > 0,
                "last_check": lc if lc > 0 else None,
                "next_check": nc if nc > 0 else None,
                "state_type": _STATE_TYPE_MAP.get(row_int(r, 10, default=1), "HARD"),
                "current_attempt": row_int(r, 11),
                "max_attempts": row_int(r, 12),
                "last_state_change": lsc if lsc > 0 else None,
                "notifications_enabled": row_bool(r, 14, default=True),
                "active_checks_enabled": row_bool(r, 15, default=True),
                "services_summary": _services_summary_from_row(r, 16),
            }
            # Federated multisite tags rows with site_id; single-site connections
            # don't, but consumers (FlowMap site umbrella, drawer aggregation)
            # still want a stable identifier to group hosts under.
            row["site_id"] = _default_site_id(site_id)
            result.append(row)
        return result

    @override
    async def get_host_services(self, hostname: str, only_hard: bool = False) -> list[ServiceRow]:
        state_col = "last_hard_state" if only_hard else "state"
        rows = await self._query(
            "GET services\n"
            f"Filter: host_name = {lqencode(hostname)}\n"
            f"Columns: description {state_col} plugin_output acknowledged scheduled_downtime_depth "
            "last_state_change is_flapping\n"
        )
        return [
            ServiceRow(
                name=row_str(r, 0),
                state=SERVICE_STATE_MAP.get(row_int(r, 1), "UNKNOWN"),
                output=row_str(r, 2),
                acknowledged=bool(row_int(r, 3)),
                in_downtime=row_int(r, 4) > 0,
                last_state_change=row_float_or_none(r, 5),
                is_flapping=bool(row_int(r, 6)),
            )
            for r in rows
        ]

    @override
    async def search_services(
        self,
        *,
        host_terms: list[str],
        service_terms: list[str],
        any_terms: list[str],
        limit: int,
        only_hard: bool = False,
    ) -> list[ServiceMatchRow]:
        conds = len(service_terms) + len(host_terms) + len(any_terms)
        if conds == 0:
            return []
        state_col = "last_hard_state" if only_hard else "state"

        # ``~~`` is a case-insensitive *regex* match, so the needle is regex-escaped
        # to behave as a literal substring — otherwise a service name with a regex
        # metachar (``Filesystem /var (NFS)``, ``CPU (3)``, ``c++``) would mis-match
        # or, with an unbalanced ``(``/``+``, make Livestatus reject the query.
        # Livestatus combines bare Filter lines with AND by default; each bare term
        # collapses its two columns with ``Or: 2`` first, then a trailing ``And:``
        # ANDs all the resulting conditions together.
        def _rx(needle: str) -> str:
            return lqencode(re.escape(needle))

        filters = ""
        for t in service_terms:
            filters += f"Filter: description ~~ {_rx(t)}\n"
        for t in host_terms:
            filters += f"Filter: host_name ~~ {_rx(t)}\n"
        for t in any_terms:
            filters += f"Filter: host_name ~~ {_rx(t)}\nFilter: description ~~ {_rx(t)}\nOr: 2\n"
        if conds > 1:
            filters += f"And: {conds}\n"
        # limit + 1 so the caller can distinguish a full page from a truncated one.
        tagged = await self._query_with_site(
            f"GET services\n"
            f"Columns: host_name description {state_col} plugin_output acknowledged "
            f"scheduled_downtime_depth last_state_change is_flapping\n"
            f"{filters}Limit: {limit + 1}\n"
        )
        return [
            ServiceMatchRow(
                host_name=row_str(r, 0),
                name=row_str(r, 1),
                state=SERVICE_STATE_MAP.get(row_int(r, 2), "UNKNOWN"),
                output=row_str(r, 3),
                acknowledged=bool(row_int(r, 4)),
                in_downtime=row_int(r, 5) > 0,
                last_state_change=row_float_or_none(r, 6),
                is_flapping=bool(row_int(r, 7)),
                site_id=_default_site_id(sid),
            )
            for sid, r in tagged
        ]

    @override
    async def get_hosts_with_geo(
        self, *, group_type: str | None = None, group_name: str | None = None
    ) -> list[GeoHost]:
        """Return every host whose monitoring data carries geo-coordinates.

        Reads the maps_lat / maps_lng labels first, then the legacy LAT / LONG
        custom vars as fallback. Hosts without geo data are filtered out so the
        worldmap automap source receives a clean list.

        The geo predicate is pushed into Livestatus so that an ``all_hosts``
        automap doesn't transfer every host's labels + custom variables each
        tick — only the geo-tagged ones cross the socket. The Python pass below
        stays authoritative: it re-validates the lat/lng pair and parses the
        values, so over-matching here (e.g. a host with maps_lat but no
        maps_lng) is harmless rather than a silent omission.
        """
        # (maps_lat AND maps_lng labels) OR (LAT AND LONG custom vars). The
        # ``labels ~~ key .`` form matches a label key with any non-empty value;
        # ``custom_variable_names >= NAME`` matches the list-membership. Keys
        # come from cmk.maps.shared.geo so the pushed-down filter can't drift
        # from resolve_host_coords below.
        geo_filter = (
            f"Filter: labels ~~ {LAT_LABEL} .\n"
            f"Filter: labels ~~ {LNG_LABEL} .\n"
            "And: 2\n"
            f"Filter: custom_variable_names >= {LAT_VAR}\n"
            f"Filter: custom_variable_names >= {LNG_VAR}\n"
            "And: 2\n"
            "Or: 2\n"
        )
        group_filter = ""
        if group_type == "hostgroup" and group_name:
            group_filter = f"Filter: groups >= {lqencode(group_name)}\n"
        elif group_type == "servicegroup" and group_name:
            # servicegroup membership lives on the services table; resolve to
            # the unique host names that own a member service.
            svc_rows = await self._query(
                f"GET services\nColumns: host_name\nFilter: groups >= {lqencode(group_name)}\n"
            )
            host_names = {row_str(r, 0) for r in svc_rows if row_str(r, 0)}
            if not host_names:
                return []
            host_filters = "".join(f"Filter: name = {lqencode(h)}\n" for h in host_names)
            group_filter = f"{host_filters}Or: {len(host_names)}\n"

        # Each block leaves one combined expression on the stack; AND them.
        filt = geo_filter if not group_filter else f"{geo_filter}{group_filter}And: 2\n"

        query = (
            "GET hosts\n"
            "Columns: name alias labels custom_variable_names custom_variable_values\n" + filt
        )
        rows = await self._query(query)
        out: list[GeoHost] = []
        for r in rows:
            name = row_str(r, 0)
            if not name:
                continue
            alias = row_str(r, 1) or name
            labels = row_dict(r, 2)
            names = row_list(r, 3)
            values = row_list(r, 4)
            cv = {str(n): v for n, v in zip(names, values, strict=False) if isinstance(n, str)}
            coords = resolve_host_coords(labels, cv)
            if coords is None:
                continue
            out.append(GeoHost(name=name, alias=alias, lat=coords[0], lng=coords[1]))
        return out

    @override
    async def get_metric_history(
        self,
        host: str,
        service: str | None,
        start: int,
        end: int,
    ) -> MetricHistoryResult:
        """Fetch metric history.

        Uses Checkmk Web API (webapi.py) when automation credentials are configured
        (Checkmk Raw / Nagios core). Falls back to Livestatus rrddata column otherwise
        (Checkmk Enterprise / CMC only).
        """
        if self._checkmk_url and self._automation_user and self._automation_secret:
            return await self._fetch_cmk_graph_history(host, service, start, end)
        return await self._fetch_rrddata_history(host, service, start, end)

    async def _fetch_cmk_graph_history(
        self,
        host: str,
        service: str | None,
        start: int,
        end: int,
    ) -> MetricHistoryResult:
        """Fetch metric history via Checkmk 2.x REST API (works with Nagios/Raw core)."""
        base_auth = self._cmk_base_and_auth()
        if base_auth is None:
            return MetricHistoryResult()
        base_url, auth_header = base_auth
        parts = base_url.rstrip("/").split("/")
        site = parts[-2] if len(parts) >= 2 and parts[-1] == "check_mk" else parts[-1]
        api_url = base_url + "/api/1.0/domain-types/metric/actions/get/invoke"

        try:
            if service:
                perf_data, _check_command = await self.get_service_perf_and_cmd(host, service)
            else:
                perf_data = (await self.get_host_state(host)).perf_data or ""
        except Exception as exc:
            logger.debug("Failed to get perf_data from Livestatus: %(error)s", {"error": exc})
            perf_data = ""
        metric_names = [m["label"] for m in parse_perf_metrics(perf_data)]
        if not metric_names:
            metric_names = await self._get_cmk_metric_names(host, service, base_url, auth_header)
        if not metric_names:
            return MetricHistoryResult()

        start_dt = datetime.fromtimestamp(start, tz=UTC).isoformat()
        end_dt = datetime.fromtimestamp(end, tz=UTC).isoformat()

        series: dict[str, list[tuple[float, float, str]]] = {}
        titles: dict[str, str] = {}
        try:
            async with httpx.AsyncClient(verify=self._tls_verify, timeout=self._timeout) as client:
                for metric_id in metric_names[:5]:
                    body = {
                        "time_range": {"start": start_dt, "end": end_dt},
                        "site": site,
                        "host_name": host,
                        "service_description": service or "",
                        "type": "single_metric",
                        "metric_id": metric_id,
                    }
                    try:
                        resp = await client.post(
                            api_url,
                            json=body,
                            headers={"Authorization": auth_header, "Accept": "application/json"},
                        )
                        if resp.status_code != 200:
                            logger.debug(
                                "CMK REST API %(metric_id)s: HTTP %(status_code)s",
                                {"metric_id": metric_id, "status_code": resp.status_code},
                            )
                            continue
                        data = resp.json()
                    except Exception as exc:
                        logger.debug(
                            "CMK REST API request failed for %(metric_id)s: %(error)s",
                            {"metric_id": metric_id, "error": exc},
                        )
                        continue

                    step = float(data.get("step", 60))
                    try:
                        ts_start = datetime.fromisoformat(
                            data.get("time_range", {}).get("start", "")
                        ).timestamp()
                    except Exception:
                        ts_start = float(start)

                    for metric in data.get("metrics", []):
                        unit_obj = metric.get("unit", {}) or {}
                        unit = unit_obj.get("symbol", "") or ""
                        points: list[tuple[float, float, str]] = [
                            (ts_start + i * step, float(v), unit)
                            for i, v in enumerate(metric.get("data_points", []))
                            if v is not None
                        ]
                        if points:
                            series[metric_id] = points
                            title = metric.get("title", "") or ""
                            if title:
                                titles[metric_id] = title
                            break
        except Exception as exc:
            logger.warning("CMK REST API metric history failed: %(error)s", {"error": exc})
        return MetricHistoryResult(series=series, titles=titles)

    async def _get_cmk_metric_names(
        self,
        host: str,
        service: str | None,
        base_url: str,
        auth_header: str,
    ) -> list[str]:
        """Fallback: get metric names via Checkmk REST API service endpoint."""
        if not service:
            return []
        # 2.5 removed the GET flavour of /domain-types/service/collections/all
        # (deprecated since 2.4); the POST endpoint takes host_name and
        # columns in the JSON body.
        url = base_url + "/api/1.0/domain-types/service/collections/all"
        try:
            async with httpx.AsyncClient(verify=self._tls_verify, timeout=self._timeout) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": auth_header,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json={"host_name": host, "columns": ["metrics", "description"]},
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
                for item in data.get("value", []):
                    ext = item.get("extensions", {})
                    if ext.get("description") == service:
                        metrics = ext.get("metrics", [])
                        return list(metrics) if metrics else []
                return []
        except Exception as exc:
            logger.warning("CMK REST API metric names fallback failed: %(error)s", {"error": exc})
            return []

    async def _fetch_rrddata_history(
        self,
        host: str,
        service: str | None,
        start: int,
        end: int,
    ) -> MetricHistoryResult:
        """Fetch metric history via Livestatus rrddata column (Checkmk Enterprise/CMC only)."""
        logger.debug(
            "rrddata fetch: host=%(host)r service=%(service)r start=%(start)d end=%(end)d",
            {"host": host, "service": service, "start": start, "end": end},
        )

        try:
            if service:
                perf_data, _check_command = await self.get_service_perf_and_cmd(host, service)
            else:
                perf_data = (await self.get_host_state(host)).perf_data or ""
        except Exception as exc:
            logger.warning(
                "rrddata: failed to get state for %(host)r/%(service)r: %(error)s",
                {"host": host, "service": service, "error": exc},
            )
            return MetricHistoryResult()

        metrics = parse_perf_metrics(perf_data)
        if not metrics:
            logger.debug(
                "rrddata: no metrics in perf_data for %(host)r/%(service)r",
                {"host": host, "service": service},
            )
            return MetricHistoryResult()

        # CMC/CEE rrddata column format:
        #   rrddata:m1:{metric}.average:{start}:{end}:{step}:{max_entries}
        # step=1 lets CMC pick the finest available RRD archive automatically.
        # max_entries caps the number of returned data points.
        window = end - start
        max_entries = min(max(window // 60, 60), 500)

        # pnp_cleanup: the metric name is a path/column element, so spaces, colons
        # and slashes (Filesystem metrics!) must be sanitized the same way CMC
        # stored them — otherwise the rrddata column spec addresses the wrong RRD.
        # lqencode on top: pnp_cleanup leaves newlines intact, and the label
        # derives from (agent-influenced) perf_data, so a newline would otherwise
        # inject extra lines into the Columns: clause.
        rrd_cols = " ".join(
            f"rrddata:m1:{lqencode(pnp_cleanup(m['label']))}.average:{start}:{end}:1:{max_entries}"
            for m in metrics
        )
        if service:
            query = (
                f"GET services\n"
                f"Columns: {rrd_cols}\n"
                f"Filter: host_name = {lqencode(host)}\n"
                f"Filter: description = {lqencode(service)}\n"
            )
        else:
            query = f"GET hosts\nColumns: {rrd_cols}\nFilter: name = {lqencode(host)}\n"

        try:
            rows = await self._query(query)
        except Exception as exc:
            logger.warning(
                "rrddata query failed for %(host)r/%(service)r (CMC/Enterprise required): %(error)s",
                {"host": host, "service": service, "error": exc},
            )
            logger.debug("rrddata failed query was:\n%(query)s", {"query": query})
            return MetricHistoryResult()

        if not rows or not rows[0]:
            logger.debug(
                "rrddata: empty result for %(host)r/%(service)r "
                "(no rrddata support or no data in range)",
                {"host": host, "service": service},
            )
            return MetricHistoryResult()

        # CMC returns each rrddata column as a flat list:
        #   [actual_start, actual_end, actual_step, v0, v1, ..., vN]
        # A value of None means no RRD file / metric exists for this column.
        # Raw values + raw unit are returned as-is; registry titles, canonical
        # scales/units and graph grouping are display semantics the client
        # resolves via the GUI (the maps_metric_info endpoint) — this daemon only
        # ships the data.
        series: dict[str, list[tuple[float, float, str]]] = {}
        row = rows[0]
        for i, m in enumerate(metrics):
            if i >= len(row):
                continue
            rrd = row[i]
            if not rrd or not isinstance(rrd, list) or len(rrd) < 4:
                continue
            try:
                actual_start = float(rrd[0])
                actual_step = float(rrd[2])
                values = rrd[3:]
                label = m["label"]
                perf_unit = m["unit"]
                points: list[tuple[float, float, str]] = [
                    (actual_start + j * actual_step, float(v), perf_unit)
                    for j, v in enumerate(values)
                    if v is not None
                ]
                if points:
                    series[label] = points
            except (IndexError, TypeError, ValueError) as exc:
                logger.debug(
                    "rrddata: failed to parse metric %(label)r: %(error)s, raw=%(raw)r",
                    {"label": m["label"], "error": exc, "raw": rrd},
                )
                continue

        logger.debug(
            "rrddata: returning %(metric_count)d metrics for %(host)r/%(service)r",
            {"metric_count": len(series), "host": host, "service": service},
        )
        return MetricHistoryResult(series=series)

    @override
    async def is_available(self) -> bool:
        # The cmk client raises on connect / protocol errors, so a clean return
        # here genuinely means the connection talked Livestatus end-to-end. The
        # query itself can return zero rows for an empty cluster — that's fine.
        try:
            await self._query("GET hosts\nColumns: name\nLimit: 1\n")
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Checkmk REST API credentials (metric history on Nagios/Raw cores)
    # ------------------------------------------------------------------

    def _cmk_base_and_auth(self) -> tuple[str, str] | None:
        """Normalised GUI base URL + Bearer header, or None without REST creds.

        A site-relative ``checkmk_url`` (``/<site>/check_mk``) is reachable via
        the local webserver, so it gets the ``http://127.0.0.1`` origin.
        """
        if not (self._checkmk_url and self._automation_user and self._automation_secret):
            return None
        cmk_url = self._checkmk_url.rstrip("/")
        if cmk_url.startswith("/"):
            cmk_url = "http://127.0.0.1" + cmk_url
        return cmk_url, f"Bearer {self._automation_user} {self._automation_secret}"

    # ------------------------------------------------------------------
    # Batch query methods
    # ------------------------------------------------------------------

    @override
    async def get_hosts_states(
        self, hostnames: list[str], only_hard: bool = False
    ) -> dict[str, ObjectState]:
        if not hostnames:
            return {}
        state_col = "last_hard_state" if only_hard else "state"
        filters = "".join(f"Filter: name = {lqencode(h)}\n" for h in hostnames)
        if len(hostnames) > 1:
            filters += f"Or: {len(hostnames)}\n"
        tagged = await self._query_with_site(
            f"GET hosts\n"
            f"Columns: name {state_col} plugin_output perf_data acknowledged "
            f"scheduled_downtime_depth {_HOST_EXTRA_COLS}\n"
            f"{filters}"
        )
        return _worst_state_dict(
            _parse_host_state_row(r, site_id=_default_site_id(sid)) for sid, r in tagged
        )

    @override
    async def get_all_hosts_states(self, only_hard: bool = False) -> dict[str, ObjectState]:
        state_col = "last_hard_state" if only_hard else "state"
        tagged = await self._query_with_site(
            f"GET hosts\n"
            f"Columns: name {state_col} plugin_output perf_data acknowledged "
            f"scheduled_downtime_depth {_HOST_EXTRA_COLS}\n"
        )
        return _worst_state_dict(
            _parse_host_state_row(r, site_id=_default_site_id(sid)) for sid, r in tagged
        )

    @override
    async def get_folder_tree(
        self, *, only_hard: bool = False, sites: list[str] | None = None
    ) -> FolderTreeData:
        # Host rows tagged with their WATO folder (from ``filename``) + a
        # service-count summary for worst-state bubbling. Real folder titles,
        # empty folders and the effective read-permitted contact groups come from
        # the GUI-prepared skeleton (``_load_wato_folders`` → ``folder_perms.mk``),
        # not from a ``.wato`` walk here.
        state_col = "last_hard_state" if only_hard else "state"
        tagged = await self._query_with_site(
            f"GET hosts\n"
            f"Columns: name filename {state_col} plugin_output acknowledged "
            f"scheduled_downtime_depth num_services_ok num_services_warn "
            f"num_services_crit num_services_unknown num_services_pending "
            f"is_flapping last_state_change\n"
        )
        site_filter = set(sites) if sites else None
        hosts: list[FolderTreeHostRow] = []
        rows_by_site: dict[str, list[FolderTreeHostRow]] = {}
        for sid, row in tagged:
            site = _default_site_id(sid)
            if site_filter is not None and site not in site_filter:
                continue
            host_row: FolderTreeHostRow = {
                "host_name": row_str(row, 0),
                "folder_path": _folder_path_from_filename(row_str(row, 1)),
                "state": HOST_STATE_MAP.get(row_int(row, 2), "UNKNOWN"),
                "output": row_str(row, 3),
                "site_id": site,
                "acknowledged": row_int(row, 4) > 0,
                "in_downtime": row_int(row, 5) > 0,
                "services_summary": _services_summary_from_row(row, 6),
                "is_flapping": row_int(row, 11) > 0,
                "last_state_change": row_float_or_none(row, 12),
            }
            hosts.append(host_row)
            rows_by_site.setdefault(site, []).append(host_row)

        # Per-site trust (distributed): a federation site that stops answering
        # silently drops out of MultiSiteConnection results — its hosts would
        # vanish from the tree and the map would read "all green". Replay the
        # last successful fetch for dead sites instead, marked ``stale`` so the
        # UI greys them out. The cache is keyed by the auth scope (a contact-
        # scoped user must never see another user's host rows) + site filter.
        dead_sites = sorted(self._mc_dead) if self._sites else []
        cache_key = (_auth_user_ctx.get(), tuple(sorted(sites)) if sites else None)
        # Bound the per-scope cache: SSE groups are few, but REST calls from
        # rotating contact-scoped users would otherwise accumulate forever.
        # FIFO eviction via dict insertion order is plenty here.
        while len(self._ft_rows_cache) > 32 and cache_key not in self._ft_rows_cache:
            self._ft_rows_cache.pop(next(iter(self._ft_rows_cache)))
        site_cache = self._ft_rows_cache.setdefault(cache_key, {})
        for site, site_rows in rows_by_site.items():
            site_cache[site] = site_rows
        replayed_dead: list[str] = []
        for site in dead_sites:
            if site_filter is not None and site not in site_filter:
                continue
            replayed_dead.append(site)
            for cached_row in site_cache.get(site, []):
                hosts.append(cast("FolderTreeHostRow", {**cached_row, "stale": True}))
        # Scope the (otherwise unscoped) folder skeleton to what the requesting
        # user may *read* in SETUP, mirroring Checkmk folder permissions
        # (``wato.see_all_folders`` OR membership in a folder's contact groups).
        # This is deliberately NOT the monitoring scope: a see-all guest sees
        # every host yet must not see SETUP folder names outside their groups.
        # ``None`` scope = unrestricted. Empty folders the user
        # can't read are then pruned by the state service.
        folders = await _load_wato_folders()
        scope = _folder_scope_ctx.get()
        scoped: list[FolderInfo] = [
            cast(
                "FolderInfo",
                {**f, "permitted": scope is None or scope.permits(f.get("permitted_groups", []))},
            )
            for f in folders
        ]
        return FolderTreeData(folders=scoped, hosts=hosts, dead_sites=replayed_dead)

    @override
    async def get_all_services_states(
        self, only_hard: bool = False
    ) -> dict[tuple[str, str], ObjectState]:
        state_col = "last_hard_state" if only_hard else "state"
        tagged = await self._query_with_site(
            f"GET services\n"
            f"Columns: host_name description {state_col} plugin_output perf_data "
            f"acknowledged scheduled_downtime_depth {_SVC_EXTRA_COLS}\n"
        )
        return _worst_state_dict(
            _parse_service_state_row(r, site_id=_default_site_id(sid)) for sid, r in tagged
        )

    @override
    async def get_services_states(
        self, pairs: list[tuple[str, str]], only_hard: bool = False
    ) -> dict[tuple[str, str], ObjectState]:
        if not pairs:
            return {}
        state_col = "last_hard_state" if only_hard else "state"
        filter_lines = ""
        for host, svc in pairs:
            filter_lines += (
                f"Filter: host_name = {lqencode(host)}\n"
                f"Filter: description = {lqencode(svc)}\n"
                f"And: 2\n"
            )
        if len(pairs) > 1:
            filter_lines += f"Or: {len(pairs)}\n"
        tagged = await self._query_with_site(
            f"GET services\n"
            f"Columns: host_name description {state_col} plugin_output perf_data "
            f"acknowledged scheduled_downtime_depth {_SVC_EXTRA_COLS}\n"
            f"{filter_lines}"
        )
        return _worst_state_dict(
            _parse_service_state_row(r, site_id=_default_site_id(sid)) for sid, r in tagged
        )

    # Above this host count we drop the per-host filter list and post-filter
    # in Python — mirrors cmk.gui.nodevis.topology._fetch_data: the core
    # spends more on filter evaluation than on returning all rows.
    _SERVICES_SUMMARY_FILTER_THRESHOLD = 500
    # Result cache TTL — slightly under the default refresh interval so a
    # second concurrent refresh of the same map (multi-tab, multi-user) can
    # hit the cache.
    _SERVICES_SUMMARY_CACHE_TTL = 4.0

    @override
    async def get_services_summary(self, hostnames: list[str]) -> dict[str, ServicesSummary]:
        """Return service-state counts per host.

        Reads the per-host ``num_services_{ok,warn,crit,unknown,pending}``
        columns straight from the ``hosts`` table — Livestatus core maintains
        them as O(1) counters, so this is a single round-trip regardless of
        host count and multisite-safe (each row is self-contained per host;
        sites merge by simple row concatenation).
        """
        if not hostnames:
            return {}

        cache_key = (_auth_user_ctx.get(), frozenset(hostnames))
        cached = self._services_summary_cache.get(cache_key, ttl=self._SERVICES_SUMMARY_CACHE_TTL)
        if cached is not None:
            return dict(cached)

        query_all = len(hostnames) > self._SERVICES_SUMMARY_FILTER_THRESHOLD
        if query_all:
            filters = ""
        else:
            filters = "".join(f"Filter: name = {lqencode(h)}\n" for h in hostnames)
            if len(hostnames) > 1:
                filters += f"Or: {len(hostnames)}\n"
        query = (
            "GET hosts\n"
            "Columns: name num_services_ok num_services_warn num_services_crit "
            "num_services_unknown num_services_pending\n"
            f"{filters}"
        )
        try:
            rows = await self._query(query)
        except Exception:
            logger.warning("services-summary query failed", exc_info=True)
            return {h: ServicesSummary() for h in hostnames}

        wanted = set(hostnames) if query_all else None
        merged: dict[str, ServicesSummary] = {h: ServicesSummary() for h in hostnames}
        for r in rows:
            name = row_str(r, 0)
            if not name:
                continue
            if wanted is not None and name not in wanted:
                continue
            merged[name] = _services_summary_from_row(r, 1)

        self._services_summary_cache.set(cache_key, merged)
        return dict(merged)

    @override
    async def get_hosts_services_batch(self, hostnames: list[str]) -> dict[str, list[ServiceRow]]:
        if not hostnames:
            return {}
        chunk_size = settings.flow_map_bulk_service_chunk_size

        async def _query_chunk(hosts: list[str]) -> list[LivestatusRow]:
            filters = "".join(f"Filter: host_name = {lqencode(h)}\n" for h in hosts)
            if len(hosts) > 1:
                filters += f"Or: {len(hosts)}\n"
            return await self._query(
                "GET services\n"
                "Columns: host_name description state plugin_output "
                "acknowledged scheduled_downtime_depth notifications_enabled "
                "last_state_change last_check next_check\n" + filters
            )

        async def _bounded_query_chunk(hosts: list[str]) -> list[LivestatusRow]:
            async with self._bulk_chunk_semaphore:
                return await _query_chunk(hosts)

        # Split top-K into smaller parallel queries: one slow host stalls only
        # its own chunk. The semaphore caps in-flight chunks so high host counts
        # (e.g. 500-host top-K → 100 chunks) don't exhaust the livestatus
        # listen backlog. ``return_exceptions=True`` lets a single failed chunk
        # degrade gracefully (those hosts get an empty service list) instead of
        # killing the whole topology broadcast.
        chunks = [hostnames[i : i + chunk_size] for i in range(0, len(hostnames), chunk_size)]
        chunk_results = await asyncio.gather(
            *(_bounded_query_chunk(c) for c in chunks),
            return_exceptions=True,
        )

        results: dict[str, list[ServiceRow]] = {h: [] for h in hostnames}
        for rows in chunk_results:
            if isinstance(rows, BaseException):
                logger.warning("services chunk failed", exc_info=rows)
                continue
            for r in rows:
                results[row_str(r, 0)].append(
                    ServiceRow(
                        name=row_str(r, 1),
                        state=SERVICE_STATE_MAP.get(row_int(r, 2), "UNKNOWN"),
                        output=row_str(r, 3),
                        acknowledged=bool(row_int(r, 4)),
                        in_downtime=row_int(r, 5) > 0,
                        notifications_enabled=bool(row_int(r, 6)),
                        last_state_change=row_float_or_none(r, 7),
                        last_check=row_float_or_none(r, 8),
                        next_check=row_float_or_none(r, 9),
                    )
                )
        return results

    # ------------------------------------------------------------------
    # Low-level socket communication
    # ------------------------------------------------------------------

    async def _query(self, query: str) -> list[LivestatusRow]:
        """Run a Livestatus query, stripping the federated site_id prefix."""
        return [row for _, row in await self._query_with_site(query)]

    def _adopt_sites_if_appeared(self) -> None:
        """Switch a federation-eligible connection to multisite when the prepared
        sitespecs file appears after startup.

        ``self._sites`` is resolved once at construction. A central site with no
        distributed setup yet — or one whose specs were written only after the
        daemon started (e.g. Maps installed onto an existing distributed central,
        or sites saved while the daemon was already running) — would otherwise
        stay on the single-socket path, showing only local hosts, until the next
        daemon restart. Watching the file mtime here lets a newly-distributed
        setup federate live. The reverse transitions (specs change or shrink back
        to a single local site) are handled by ``_run_multisite_sync``'s rebuild
        path once we are on the multisite path.
        """
        if self._sites or not self._federation_eligible:
            return
        mtime = _cmk_sites.sites_mk_mtime()
        if mtime in (0.0, self._single_mode_mtime):
            return
        self._single_mode_mtime = mtime
        loaded = _cmk_sites.load_sites()
        if loaded:
            self._sites = loaded
            logger.info(
                "Livestatus federation enabled at runtime: sitespecs appeared "
                "(%(site_count)d sites: %(sites)s)",
                {"site_count": len(loaded), "sites": ", ".join(sorted(loaded))},
            )

    async def _query_with_site(self, query: str) -> list[tuple[str | None, LivestatusRow]]:
        """Run a query and return ``(site_id, row)`` tuples.

        Single-site connections yield ``site_id=None`` so callers can remain
        connection-agnostic.
        """
        self._adopt_sites_if_appeared()
        if self._sites:
            async with self._semaphore:
                rows = await asyncio.wait_for(
                    asyncio.to_thread(self._run_multisite_sync, query),
                    timeout=settings.connection_query_timeout,
                )
            return [
                (str(row[0]) if row and isinstance(row[0], str) else None, row[1:]) for row in rows
            ]
        async with self._semaphore:
            single_rows = await asyncio.wait_for(
                asyncio.to_thread(self._run_singlesite_sync, query),
                timeout=settings.connection_query_timeout,
            )
        return [(None, r) for r in single_rows]

    def _make_singlesite_connection(self) -> SingleSiteConnection:
        """Fresh connection per call so no socket is shared across worker threads."""
        from cmk.livestatus_client import SingleSiteConnection

        conn = SingleSiteConnection(
            self._ss_socketurl,
            tls=self._use_tls,
            verify=self._tls_verify,
            ca_file_path=self._ss_ca_file,
        )
        # ceil, not int(): set_timeout takes whole seconds and
        # socket.settimeout(0) would mean non-blocking, not "0.5s".
        conn.set_timeout(max(1, math.ceil(self._timeout)))
        return conn

    def _run_singlesite_sync(self, lql: str) -> list[LivestatusRow]:
        """Sync single-site query via Checkmks ``SingleSiteConnection``.

        Must run in a worker thread (``asyncio.to_thread``); the client is
        sync. The client adds OutputFormat/ResponseHeader framing itself, so
        *lql* is the bare query — same contract as ``_run_multisite_sync``.
        """
        headers = ""
        auth_user = _auth_user_ctx.get()
        if auth_user:
            headers += f"AuthUser: {lqencode(auth_user)}\n"
        conn = self._make_singlesite_connection()
        try:
            return list(conn.query(_lql_to_query(lql), add_headers=headers))
        finally:
            # The client sends ``KeepAlive: on`` and only disconnects on
            # query errors — close explicitly instead of relying on GC.
            conn.disconnect()

    # MultiSiteConnection marks unreachable sites dead at CONNECT time and
    # never retries them for its lifetime (cmk.gui sidesteps this by building
    # a fresh connection per request). With our cached MC a dead federation
    # site would stay dead until the daemon restarts — rebuild periodically
    # while anything is dead so recovered sites come back. Trade-off: the
    # rebuild happens under _mc_lock, so a SYN-blackholed site (machine gone,
    # not just process down) can stall concurrent queries for one connect
    # timeout every retry interval — still far less often than cmk.gui's
    # connect-per-request.
    _MC_DEAD_RETRY_SECONDS = 30.0

    def _mc_needs_rebuild(self, current_mtime: float) -> bool:
        if self._mc is None or current_mtime != self._mc_mtime:
            return True
        return bool(
            self._mc_dead and time.monotonic() - self._mc_built_at > self._MC_DEAD_RETRY_SECONDS
        )

    def _run_multisite_sync(
        self, lql: str, only_sites: list[str] | None = None
    ) -> list[list[object]]:
        """Sync federated query via Checkmks ``MultiSiteConnection``.

        Must run in a worker thread (``asyncio.to_thread``); ``MultiSiteConnection``
        is sync. ``AuthUser:`` is sent per-query so the cached connection isn't
        mutated across concurrent users.
        """
        from cmk.livestatus_client import MultiSiteConnection, SiteConfigurations

        if not self._sites:
            return []

        with self._mc_lock:
            current_mtime = _cmk_sites.sites_mk_mtime()
            if self._mc_needs_rebuild(current_mtime):
                if self._mc is not None and current_mtime != self._mc_mtime:
                    logger.info("Site specs changed — reloading enabled sites")
                self._sites = _cmk_sites.load_sites()
                if not self._sites:
                    self._mc = None
                    self._mc_mtime = current_mtime
                    self._mc_dead = set()
                    return []
                if self._mc is not None:
                    # Close the superseded connection's sockets — dead-retry
                    # rebuilds every 30s would otherwise leak FDs until GC.
                    with contextlib.suppress(Exception):
                        self._mc.disconnect()
                self._mc = MultiSiteConnection(
                    sites=SiteConfigurations(cast("dict[SiteId, SiteConfiguration]", self._sites))
                )
                self._mc.set_prepend_site(True)
                self._mc_mtime = current_mtime
                self._mc_built_at = time.monotonic()
                # Deliberately NOT clearing _mc_dead here: a still-dead site
                # must stay marked until the post-query dead_sites() refresh,
                # or its stale foldertree leaves would flicker out for a tick.
            mc = self._mc
            assert mc is not None  # rebuilt above when missing

            headers = ""
            auth_user = _auth_user_ctx.get()
            if auth_user:
                headers += f"AuthUser: {lqencode(auth_user)}\n"

            mc.set_only_sites([SiteId(s) for s in only_sites] if only_sites else None)
            try:
                rows = mc.query(lql, add_headers=headers)
            finally:
                mc.set_only_sites(None)

            self._log_dead_site_transitions(
                cast("Mapping[str, Mapping[str, object]]", mc.dead_sites())
            )
            return list(rows)

    def _log_dead_site_transitions(self, dead: Mapping[str, Mapping[str, object]]) -> None:
        """Log only when a site enters or leaves the dead set, not every query."""
        current = set(dead)
        for sid in current - self._mc_dead:
            logger.warning(
                "Livestatus site %(site_id)s dead: %(exception)s",
                {"site_id": sid, "exception": dead[sid].get("exception")},
            )
        for sid in self._mc_dead - current:
            logger.info("Livestatus site %(site_id)s recovered", {"site_id": sid})
        self._mc_dead = current
