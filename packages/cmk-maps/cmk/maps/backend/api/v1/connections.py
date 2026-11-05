#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Connection configuration API."""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from cmk.maps.backend.api.v1.deps import (
    can_configure,
    rate_limited_read,
    require_connection_read,
    resolve_auth_user,
)
from cmk.maps.backend.connections.base import (
    ConnectionBase,
    ServiceRow,
    topology_problem_rank,
    TopologyRow,
)
from cmk.maps.backend.core.auth import Principal
from cmk.maps.backend.schemas.connection import (
    ConnectionListEntry,
    to_list_entry,
)
from cmk.maps.backend.schemas.state import ObjectDetails
from cmk.maps.backend.schemas.topology import (
    ServiceNode,
    TopologyNode,
)
from cmk.maps.backend.services import connection_service
from cmk.maps.backend.services.state_service import (
    get_connection,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@asynccontextmanager
async def auth_user_scope(connection: ConnectionBase, auth_user: str | None) -> AsyncIterator[None]:
    """Scope livestatus queries inside the block to *auth_user*'s contact
    visibility; ``None`` (admins / ``general.see_all`` / non-CMK setups) runs
    UNSCOPED. Livestatus ``AuthUser`` only knows contacts, and cmkadmin
    typically is no contact, so passing the raw username would silently
    filter every query down to zero rows.
    """
    if auth_user is not None:
        async with connection.with_auth_user(auth_user):
            yield
    else:
        yield


@asynccontextmanager
async def _auth_scope(connection: ConnectionBase, user: Principal) -> AsyncIterator[None]:
    """Resolve *user* to a Livestatus AuthUser and scope queries accordingly."""
    async with auth_user_scope(connection, resolve_auth_user(user)):
        yield


@router.get("", response_model=list[ConnectionListEntry])
async def list_backends(
    current_user: Principal = Depends(require_connection_read),
) -> list[ConnectionListEntry]:
    full = can_configure(current_user)
    return [to_list_entry(b, full=full) for b in connection_service.load_all()]


# Connection CRUD lives in Checkmk's own settings (Customize → Maps →
# "Maps settings", ConfigDomainMaps). This service is read-only: it lists
# connections (above) and runs live *read* queries against them (below).
#
# Commands (acknowledge, downtime, reschedule, …) are intentionally NOT served
# by the daemon. They run entirely GUI-side (cmk.maps.gui._commands via
# sites.live()), which means they only reach the site's own configured
# (distributed) sites — a map object on an *external* connection (a foreign
# Checkmk reached over TCP+automation, not part of this site's distributed
# setup) is command read-only for the first release.


# Worst first, as Checkmk ranks the states; PENDING sits above OK so a flapping
# service doesn't reshuffle the visible top-N.
_SERVICE_SORT_KEY = {"CRITICAL": 0, "UNKNOWN": 1, "WARNING": 2, "PENDING": 3, "OK": 4}


def _sorted_truncated_services(svcs: list[ServiceRow], limit: int) -> tuple[list[ServiceRow], int]:
    """Return (top-N services, truncated_count). Non-OK first, then OK alphabetic."""
    ordered = sorted(
        svcs,
        key=lambda s: (_SERVICE_SORT_KEY.get(s["state"], 5), s["name"]),
    )
    if limit <= 0 or len(ordered) <= limit:
        return ordered, 0
    return ordered[:limit], len(ordered) - limit


def _filter_topology(
    nodes: list[TopologyRow],
    root: str | None,
    child_layers: int | None,
    parent_layers: int | None,
) -> list[TopologyRow]:
    if not root:
        return nodes
    by_name: dict[str, TopologyRow] = {n["name"]: n for n in nodes}
    if root not in by_name:
        return []

    children_of: dict[str, list[str]] = {}
    parents_of: dict[str, list[str]] = {}
    for n in nodes:
        parents = n.get("parents") or []
        parents_of[n["name"]] = list(parents)
        for parent in parents:
            children_of.setdefault(parent, []).append(n["name"])

    def bfs(neighbours: dict[str, list[str]], depth_limit: int) -> set[str]:
        seen: set[str] = {root}
        frontier: list[str] = [root]
        depth = 0
        while frontier and (depth_limit < 0 or depth < depth_limit):
            depth += 1
            nxt: list[str] = []
            for name in frontier:
                for nb in neighbours.get(name, []):
                    if nb not in seen and nb in by_name:
                        seen.add(nb)
                        nxt.append(nb)
            frontier = nxt
        return seen

    keep = bfs(children_of, child_layers if child_layers is not None else -1)
    keep |= bfs(parents_of, parent_layers if parent_layers is not None else 0)
    return [n for n in nodes if n["name"] in keep]


_problem_count = topology_problem_rank


async def build_topology_response(
    connection: ConnectionBase,
    *,
    include_services: bool,
    services_per_host: int,
    top_affected_hosts: int,
    root: str | None = None,
    child_layers: int | None = None,
    parent_layers: int | None = None,
) -> list[TopologyNode]:
    """Fetch topology + (optionally) per-host services and return TopologyNodes.

    Shared between the REST endpoint and the broadcast loop so both produce
    identical payloads. Caller is responsible for any auth_user context and
    caching — this helper just runs the queries.
    """
    rows = await connection.get_topology()
    rows = _filter_topology(rows, root, child_layers, parent_layers)

    if not (include_services and rows):
        return [TopologyNode(**r) for r in rows]

    if top_affected_hosts <= 0:
        affected: set[str] = set()
    elif len(rows) > top_affected_hosts:
        ranked = sorted(rows, key=_problem_count, reverse=True)
        affected = {r["name"] for r in ranked[:top_affected_hosts]}
    else:
        affected = {r["name"] for r in rows}

    services_by_host = (
        await connection.get_hosts_services_batch(sorted(affected)) if affected else {}
    )

    result: list[TopologyNode] = []
    for row in rows:
        if row["name"] not in affected:
            result.append(TopologyNode(**row, services_omitted=True))
            continue
        svcs = list(services_by_host.get(row["name"], []))
        kept, truncated = _sorted_truncated_services(svcs, services_per_host)
        result.append(
            TopologyNode(
                **row,
                services=[ServiceNode.model_validate(s) for s in kept],
                services_truncated_count=truncated,
            )
        )
    return result


class MetricPoint(BaseModel):
    ts: float
    value: float
    unit: str


class MetricHistoryResponse(BaseModel):
    series: dict[str, list[MetricPoint]]
    # Display names only when the backend itself supplies them (remote REST
    # metric endpoint, demo connection); registry titles come from the GUI.
    titles: dict[str, str] = {}
    # Set (with empty series) when the backend fetch failed — details stay in
    # the server log, the client only needs "no data vs. error".
    error: str | None = None


@router.get("/{connection_id}/metric-history", response_model=MetricHistoryResponse)
async def get_metric_history(
    connection_id: str,
    host: str = Query(...),
    service: str | None = Query(None),
    minutes: int = Query(60, ge=1, le=10080),
    user: Principal = Depends(rate_limited_read),
) -> MetricHistoryResponse:
    """Return RRD metric history for a host/service using Livestatus rrddata (Checkmk only)."""
    connection = get_connection(connection_id)
    if connection is None:
        return MetricHistoryResponse(series={})
    end = int(time.time())
    start = end - minutes * 60
    try:
        async with _auth_scope(connection, user):
            raw = await connection.get_metric_history(host, service, start, end)
    except Exception:
        logger.exception("metric-history error")
        return MetricHistoryResponse(series={}, error="Metric history fetch failed")
    return MetricHistoryResponse(
        series={
            label: [MetricPoint(ts=ts, value=v, unit=u) for ts, v, u in pts]
            for label, pts in raw.series.items()
        },
        titles=raw.titles,
    )


@router.get("/{connection_id}/object-details", response_model=ObjectDetails | None)
async def get_object_details(
    connection_id: str,
    obj_type: str = Query(..., alias="type", pattern="^(host|service)$"),
    host: str = Query(...),
    service: str | None = Query(None),
    user: Principal = Depends(rate_limited_read),
) -> ObjectDetails | None:
    """Return on-demand drawer/properties details for a host or service.

    Kept off the state stream because long_output, comments,
    downtimes and topology can each be many KB and rarely change between
    checks. The Drawer fetches this once on open.
    """
    connection = get_connection(connection_id)
    if connection is None:
        return None
    async with _auth_scope(connection, user):
        if obj_type == "host":
            return await connection.get_host_details(host)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="service query parameter required for type=service",
            )
        return await connection.get_service_details(host, service)
