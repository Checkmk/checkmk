#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""State endpoints + Server-Sent Events for real-time updates."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import cast, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from cmk.maps.backend.api.v1.connections import auth_user_scope, build_topology_response
from cmk.maps.backend.api.v1.deps import (
    principal_from_token,
    rate_limited_read,
    resolve_auth_user,
)
from cmk.maps.backend.api.v1.types import MapName
from cmk.maps.backend.connections.base import ServiceMatchRow, ServiceRow
from cmk.maps.backend.core.auth import Principal
from cmk.maps.backend.core.config import settings
from cmk.maps.backend.core.ratelimit import ws_connect_limiter
from cmk.maps.backend.core.sse import manager, Subscriber
from cmk.maps.backend.integrations.checkmk import resolve_folder_scope
from cmk.maps.backend.schemas.map import FlowView, FolderTreeView, MapConfig, RadarView
from cmk.maps.backend.schemas.state import (
    FolderHostService,
    FolderServiceMatch,
    FolderServiceSearchResult,
    FolderTreeDelta,
    MapStates,
    ObjectState,
    ObjectTiming,
)
from cmk.maps.backend.schemas.stream import (
    StateUpdateMessage,
    StreamedMapStates,
    StreamMessage,
    TopologyUpdateMessage,
)
from cmk.maps.backend.schemas.topology import TopologyNode
from cmk.maps.backend.services import map_service, settings_service, state_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Shared broadcast task per active map — avoids O(n²) fetch × broadcast.
# Without this every connected client would independently fetch the topology
# + states and push to all clients.
_broadcast_tasks: dict[str, asyncio.Task[None]] = {}
# Last dead-sites list pushed per (map, subscriber-group): a federation site
# dying/recovering must reach clients even when no node-level delta exists.
_dead_sites_snapshots: dict[tuple[str, str | None], list[str]] = {}

# Heartbeat cadence for SSE keepalives. Sized below typical Apache ProxyTimeout
# (60 s default in OMD) so the stream doesn't get torn down on idle maps.
_SSE_KEEPALIVE_INTERVAL = 30.0


async def _fetch_topology_for_user(
    cfg: MapConfig, auth_user: str | None
) -> list[TopologyNode] | None:
    connection = state_service.get_connection(cfg.connection_id)
    if connection is None:
        return None

    services_per_host = settings.flow_map_max_services_per_host
    top_affected_hosts = settings.flow_map_top_affected_hosts
    root: str | None = None
    child_layers: int | None = None
    parent_layers: int | None = None
    if isinstance(cfg.view, FlowView):
        if cfg.view.max_services_per_host is not None:
            services_per_host = cfg.view.max_services_per_host
        if cfg.view.top_affected_hosts is not None:
            top_affected_hosts = cfg.view.top_affected_hosts
        root = cfg.view.root
        child_layers = cfg.view.child_layers
        parent_layers = cfg.view.parent_layers

    async def _build() -> list[TopologyNode]:
        return await build_topology_response(
            connection,
            include_services=True,
            services_per_host=services_per_host,
            top_affected_hosts=top_affected_hosts,
            root=root,
            child_layers=child_layers,
            parent_layers=parent_layers,
        )

    try:
        async with auth_user_scope(connection, auth_user):
            return await _build()
    except Exception:
        logger.warning("topology fetch failed for map '%(map)s'", {"map": cfg.name}, exc_info=True)
        return None


def _build_states_msg(
    map_name: str,
    states: MapStates,
    to_send: list[ObjectState],
    removed_ids: list[str],
    full: bool,
    timing: list[ObjectTiming],
    ft_delta: FolderTreeDelta | None,
) -> str:
    return StateUpdateMessage(
        map=map_name,
        states=StreamedMapStates(
            map_name=states.map_name,
            states=to_send,
            generated_at=states.generated_at,
            connection_ok=states.connection_ok,
            dead_sites=states.dead_sites,
            # Foldertree maps diff the tree per tick: ``full`` on the first
            # tick / a structural change, else only changed nodes. At 100k+
            # hosts the full tree is ~45MB raw, so streaming the whole thing
            # every 5s froze the client — the delta cuts that to O(changes).
            folder_tree_delta=ft_delta,
            runtime=states.runtime,
        ),
        removed_ids=removed_ids,
        full=full,
        timing=timing,
    ).model_dump_json()


def _map_key(owner: str, name: str) -> str:
    """Opaque per-stream key isolating a map by its MAP owner + name, so two
    users' same-named maps get separate cache entries, broadcast loops, and
    snapshots. NUL can't appear in either part (name is pattern-validated)."""
    return f"{owner}\x00{name}"


def _map_for_stream(user: Principal, name: str) -> MapConfig:
    """Resolve the viewed map's config under its REAL owner, or 404.

    Keyed by ``map_key_owner`` (the map's real owner for a map-scoped ticket,
    else the caller), so all viewers of a published map resolve the one config
    registered under it. A map-scoped ticket must match the requested map, so a
    ticket for one map can't be used to stream another."""
    if user.map_name is not None and name != user.map_name:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    cfg = map_service.get_map(user.map_key_owner, name)
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    return cfg


async def _push_topology_to(
    cfg: MapConfig,
    map_key: str,
    auth_user: str | None,
    targets: list[Subscriber],
    *,
    force_full: bool,
    store: bool = True,
) -> None:
    if not targets:
        return
    nodes = await _fetch_topology_for_user(cfg, auth_user)
    if nodes is None:
        return
    delta = state_service.compute_topology_delta(
        map_key, auth_user, nodes, force_full=force_full, store=store
    )
    if not (force_full or delta.added or delta.changed or delta.removed or delta.timing):
        return
    # ``map`` carries the real map name (the SPA matches messages by it); the
    # snapshot/push key is the owner-qualified map key.
    msg = TopologyUpdateMessage(map=cfg.name, delta=delta).model_dump_json()
    manager.push(map_key, targets, msg)


async def _broadcast_loop(map_key: str) -> None:
    """Fetch states once per interval and push to all subscribers.

    With CHECKMK_OMD_ROOT, subscribers are grouped by auth_user and each group
    receives states filtered to its user's contact groups. Otherwise a single
    shared query is issued.

    Delta-encoded per (map, auth_user): only added/changed states travel the
    wire, plus object_ids that disappeared. The first tick (or after a snapshot
    is dropped) is full so newly-attached subscribers converge.

    Flow Maps additionally receive ``topology_update`` deltas so the FlowMap
    component renders without its own REST polling.
    """
    owner, _, name = map_key.partition("\x00")
    logger.debug("Broadcast loop started for map '%(map)s'", {"map": name})
    try:
        while manager.get_subscriber_count(map_key) > 0:
            # Guard the whole tick: a single transient error (a Livestatus shape
            # change, one failed fetch) must not kill the loop and freeze every
            # connected viewer on stale data until someone reconnects. Log it and
            # carry on — the map recovers on the next tick.
            try:
                cfg = map_service.get_map(owner, name)
                tick_start = asyncio.get_running_loop().time()
                user_count = 0
                if cfg is not None:
                    grouped = manager.get_subscribers_grouped(map_key)
                    user_count = len(grouped)
                    # Forget delta snapshots for groups whose subscribers have all
                    # left, so a long-running map doesn't leak per-group state.
                    live_groups = set(grouped)
                    state_service.prune_group_snapshots(map_key, live_groups)
                    state_service.prune_map_snapshots(_dead_sites_snapshots, map_key, live_groups)
                    for group_key, subs in grouped.items():
                        # All subs in a group render identically; the first carries
                        # the monitoring (auth_user) + folder (folder_scope) scopes.
                        # Snapshots/deltas are keyed by group_key so admin and a
                        # see-all guest on a foldertree map don't share a tree.
                        rep = subs[0]
                        auth_user = rep.auth_user
                        states = await state_service.get_map_states(
                            cfg,
                            auth_user=auth_user,
                            folder_scope=rep.folder_scope,
                        )
                        to_send, removed_ids, is_full, timing = state_service.compute_states_delta(
                            map_key, group_key, states.states
                        )
                        # Computed unconditionally so the snapshot stays current;
                        # the tree carries its own delta (structure can shift with
                        # no host-state delta — see compute_folder_tree_delta).
                        ft_delta = (
                            state_service.compute_folder_tree_delta(
                                map_key, group_key, states.folder_tree
                            )
                            if cfg.view.type == "foldertree"
                            else None
                        )
                        ft_changed = ft_delta is not None and (
                            ft_delta.full or bool(ft_delta.changed)
                        )
                        ds_key = (map_key, group_key)
                        ds_changed = _dead_sites_snapshots.get(ds_key) != states.dead_sites
                        _dead_sites_snapshots[ds_key] = states.dead_sites
                        # A freshly (re)joined subscriber gets a full built from this
                        # same fetch; everyone else gets the delta against the shared
                        # snapshot. So a reconnect re-fulls only that client — not the
                        # whole group — without a second Livestatus query.
                        newcomers = [s for s in subs if s.needs_full]
                        established = [s for s in subs if not s.needs_full]
                        if established and (
                            is_full or to_send or removed_ids or timing or ft_changed or ds_changed
                        ):
                            msg = _build_states_msg(
                                name, states, to_send, removed_ids, is_full, timing, ft_delta
                            )
                            manager.push(map_key, established, msg)
                        if newcomers:
                            full_ft = (
                                FolderTreeDelta(full=True, tree=states.folder_tree)
                                if cfg.view.type == "foldertree"
                                else None
                            )
                            full_msg = _build_states_msg(
                                name, states, states.states, [], True, [], full_ft
                            )
                            manager.push(map_key, newcomers, full_msg)
                            for s in newcomers:
                                s.needs_full = False
                        if cfg.view.type == "flow":
                            await _push_topology_to(cfg, map_key, auth_user, subs, force_full=False)
                elapsed_ms = (asyncio.get_running_loop().time() - tick_start) * 1000
                logger.debug(
                    "Broadcast tick map=%(map)s user_groups=%(user_groups)d "
                    "elapsed=%(elapsed_ms).0fms",
                    {"map": name, "user_groups": user_count, "elapsed_ms": elapsed_ms},
                )
            except Exception:
                logger.exception("Broadcast tick error for map '%(map)s'", {"map": name})
            # Read interval fresh each tick so System-Settings changes apply
            # without restarting the backend.
            await asyncio.sleep(settings_service.get_effective_state_refresh_interval())
    finally:
        _broadcast_tasks.pop(map_key, None)
        state_service.drop_topology_snapshot(map_key)
        state_service.drop_states_snapshot(map_key)
        state_service.drop_map_snapshots(_dead_sites_snapshots, map_key)
        logger.debug("Broadcast loop stopped for map '%(map)s'", {"map": name})


_RADAR_FILTERS: set[str] = {"hostgroup", "servicegroup", "all_hosts", "all_services"}


# Returns a pre-dumped Response (passed through untouched) instead of a model:
# skips FastAPI's second full re-validation, which dominated initial load on
# 100k+-host maps. response_model stays for the OpenAPI schema (api.ts codegen).
@router.get("/maps/{name}/states", response_model=MapStates)
async def get_map_states(
    name: MapName,
    current_user: Principal = Depends(rate_limited_read),
    radar_filter: str | None = None,
    radar_filter_value: str | None = None,
    ft_override: bool = False,
    ft_root_folder: str = "",
    ft_show_empty_folders: bool = True,
    ft_only_hard_states: bool = False,
    ft_sites: list[str] = Query(default_factory=list),
) -> Response:
    cfg = _map_for_stream(current_user, name)
    # Settings-preview override for radar maps. Both query params arrive
    # together so we never mix disk-state filter with a half-edited override.
    if (
        cfg.view.type == "radar"
        and radar_filter is not None
        and radar_filter_value is not None
        and radar_filter in _RADAR_FILTERS
    ):
        cfg = cfg.model_copy(
            update={
                "view": RadarView(
                    filter=cast(
                        Literal["hostgroup", "servicegroup", "all_hosts", "all_services"],
                        radar_filter,
                    ),
                    filter_value=radar_filter_value,
                )
            }
        )
    # Settings-preview override for foldertree maps: only the server-side view
    # fields (the others are mirrored client-side and need no requery). Gated on
    # an explicit flag so an empty root_folder reads as "(all)" not "unset".
    # problems_only is forced off so the server never prunes healthy nodes — the
    # client filters it reactively, so toggling it in the preview works both ways
    # without a per-toggle tree rebuild.
    if ft_override and isinstance(cfg.view, FolderTreeView):
        cfg = cfg.model_copy(
            update={
                "view": cfg.view.model_copy(
                    update={
                        "root_folder": ft_root_folder,
                        "show_empty_folders": ft_show_empty_folders,
                        "only_hard_states": ft_only_hard_states,
                        "sites": ft_sites,
                        "problems_only": False,
                    }
                )
            }
        )
    auth_user = resolve_auth_user(current_user)
    # Only foldertree maps consume folder_scope; skip the permission/contact-group
    # lookups for every other map type.
    folder_scope = resolve_folder_scope(current_user) if cfg.view.type == "foldertree" else None
    states = await state_service.get_map_states(
        cfg,
        auth_user=auth_user,
        folder_scope=folder_scope,
    )
    return Response(content=states.model_dump_json(), media_type="application/json")


@router.get("/maps/{name}/folder-host-services", response_model=list[FolderHostService])
async def get_folder_host_services(
    name: MapName,
    host: str = Query(..., description="Host name to fetch services for"),
    current_user: Principal = Depends(rate_limited_read),
) -> list[FolderHostService]:
    """Lazily fetch a single host's services for a foldertree map.

    Only invoked when an operator expands a host in the tree/map — a single
    host-scoped Livestatus query — so the map scales to environments with
    millions of hosts (services are never pushed eagerly over SSE).
    """
    cfg = _map_for_stream(current_user, name)
    if not isinstance(cfg.view, FolderTreeView):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a foldertree map")
    connection = state_service.get_connection(cfg.connection_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    auth_user = resolve_auth_user(current_user)
    only_hard = cfg.view.only_hard_states

    async def _fetch() -> list[ServiceRow]:
        return await connection.get_host_services(host, only_hard=only_hard)

    try:
        async with auth_user_scope(connection, auth_user):
            rows = await _fetch()
    except Exception:
        logger.warning(
            "folder host-services fetch failed for '%(map)s'/%(host)s",
            {"map": name, "host": host},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Service fetch failed"
        ) from None

    services = [
        FolderHostService(
            name=r["name"],
            state=r["state"],
            output=r.get("output", ""),
            acknowledged=r.get("acknowledged", False),
            in_downtime=r.get("in_downtime", False),
            is_flapping=r.get("is_flapping", False),
            last_state_change=r.get("last_state_change"),
        )
        for r in rows
    ]
    # Worst-state first (CRITICAL on top), then alphabetical — matches the
    # host/folder ordering elsewhere in the tree.
    state_service.sort_folder_services(services)
    return services


@router.get("/maps/{name}/folder-search", response_model=FolderServiceSearchResult)
async def folder_service_search(
    name: MapName,
    s: list[str] = Query(default_factory=list, description="Service-name substrings (AND)"),
    h: list[str] = Query(default_factory=list, description="Host-name substrings (AND)"),
    q: list[str] = Query(default_factory=list, description="Bare substrings (host OR service)"),
    current_user: Principal = Depends(rate_limited_read),
) -> FolderServiceSearchResult:
    """Server-side service search for a foldertree map.

    Services are never pushed over SSE (would not scale to millions), so a
    ``s:``/bare search that should reach un-expanded hosts queries Livestatus
    directly with a hard ``Limit``. The frontend places each hit into the host
    it already has in the tree. Pure host/folder searches stay client-side and
    never call this. Terms shorter than 2 chars are dropped (too broad).
    """
    limit = settings.folder_search_max_services

    # Trim and drop sub-2-char terms (too broad); forward the trimmed value so a
    # stray space never leaks into the match.
    def _terms(raw: list[str]) -> list[str]:
        return [s for s in (t.strip() for t in raw) if len(s) >= 2]

    service_terms = _terms(s)
    host_terms = _terms(h)
    any_terms = _terms(q)
    # Only a service-bearing query reaches the backend; a pure host search is
    # answered from the already-loaded tree on the client.
    if not service_terms and not any_terms:
        return FolderServiceSearchResult(matches=[], truncated=False, limit=limit)

    cfg = _map_for_stream(current_user, name)
    if not isinstance(cfg.view, FolderTreeView):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a foldertree map")
    connection = state_service.get_connection(cfg.connection_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    auth_user = resolve_auth_user(current_user)
    only_hard = cfg.view.only_hard_states

    async def _fetch() -> list[ServiceMatchRow]:
        return await connection.search_services(
            host_terms=host_terms,
            service_terms=service_terms,
            any_terms=any_terms,
            limit=limit,
            only_hard=only_hard,
        )

    try:
        async with auth_user_scope(connection, auth_user):
            rows = await _fetch()
    except Exception:
        logger.warning("folder service search failed for '%(map)s'", {"map": name}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Service search failed"
        ) from None

    truncated = len(rows) > limit
    rows = rows[:limit]

    # Group hits by (host, site), preserving first-seen order; sort each host's
    # services worst-state first, matching the lazy folder-host-services order.
    grouped: dict[tuple[str, str | None], list[FolderHostService]] = {}
    for r in rows:
        key = (r["host_name"], r.get("site_id"))
        grouped.setdefault(key, []).append(
            FolderHostService(
                name=r["name"],
                state=r["state"],
                output=r.get("output", ""),
                acknowledged=r.get("acknowledged", False),
                in_downtime=r.get("in_downtime", False),
                is_flapping=r.get("is_flapping", False),
                last_state_change=r.get("last_state_change"),
            )
        )
    matches: list[FolderServiceMatch] = []
    for (host, site), svcs in grouped.items():
        state_service.sort_folder_services(svcs)
        matches.append(FolderServiceMatch(host=host, site_id=site, services=svcs))
    return FolderServiceSearchResult(matches=matches, truncated=truncated, limit=limit)


class SseResponse(StreamingResponse):
    """Carries the stream's media type into the schema; the body is streamed."""

    media_type: str | None = "text/event-stream"


@router.get(
    "/sse/maps/{name}",
    # The stream's frames are not a JSON response body, so FastAPI cannot infer
    # them — declaring them here is what puts them in the schema, and with it in
    # the frontend's generated types.
    response_class=SseResponse,
    responses={200: {"model": StreamMessage, "description": "One state or topology frame."}},
)
async def sse_map_states(
    name: MapName,
    request: Request,
    # Optional so a missing token fails as 401 like every other route, not as a
    # 422 that hands an unauthenticated caller the parameter schema.
    token: str | None = Query(
        None, description="Stream ticket or access token (EventSource can't set headers)"
    ),
) -> StreamingResponse:
    """SSE endpoint streaming state + topology updates for a map.

    Authentication: ``?token=`` query parameter (EventSource cannot set custom
    headers). The frontend obtains a short-lived stream ticket from the GUI and
    passes it here; the daemon validates it against the site-internal secret.
    """
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = principal_from_token(token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    # Keyed by the ticket identity: behind the site's proxies every client
    # arrives from the same address, so an IP key would share one budget site-wide.
    if ws_connect_limiter.is_blocked(user.name):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limited")
    ws_connect_limiter.record(user.name)

    # Owner = the map's REAL owner from the signed ticket (map_key_owner), never
    # a client value — so all viewers of a published map share one broadcast loop,
    # while a private map stays in its owner's namespace and no user can address
    # another's stream. Falls back to the caller for an unbound ticket.
    cfg = _map_for_stream(user, name)
    owner = user.map_key_owner
    map_key = _map_key(owner, name)

    auth_user = resolve_auth_user(user)
    # Foldertree maps render a SETUP folder skeleton scoped by folder-read
    # permission, which differs from the monitoring scope (a see-all guest shares
    # auth_user=None with an admin but sees fewer folders). Fold that into the
    # subscriber group key so they get separate computations; other map types
    # group by auth_user alone.
    folder_scope = None
    group_key: str | None = auth_user
    if cfg.view.type == "foldertree":
        folder_scope = resolve_folder_scope(user)
        group_key = f"{auth_user}#{folder_scope.key}"
    sub = manager.subscribe(map_key, auth_user, folder_scope=folder_scope, group_key=group_key)

    # Only ``event_stream``'s finally unsubscribes, and it doesn't run until the
    # StreamingResponse is driven — so any failure in the setup below would leak
    # the subscriber (queue never drained, broadcast loop never idle). Pair the
    # unsubscribe with the subscribe by unwinding it on a setup error.
    try:
        # A new subscriber must not diverge from its REST first paint on anything
        # that changed before it joined (the group snapshot already absorbed those,
        # so a plain delta would skip them). It is flagged ``needs_full`` (default
        # on a fresh Subscriber), and the broadcast loop sends it a full built from
        # the same fetch — re-fulling only this client, not the whole group.
        if map_key not in _broadcast_tasks or _broadcast_tasks[map_key].done():
            _broadcast_tasks[map_key] = asyncio.create_task(_broadcast_loop(map_key))

        # First-paint topology for Flow Maps so the client doesn't wait a full
        # broadcast tick before the initial render. ``store=False`` keeps the shared
        # snapshot intact, so the group's already-connected viewers keep getting
        # deltas (topology deltas are convergent upserts, so this client reconverges
        # from the next tick's group delta on top of this full) — no group re-full.
        if cfg.view.type == "flow":
            await _push_topology_to(cfg, map_key, auth_user, [sub], force_full=True, store=False)
    except Exception:
        manager.unsubscribe(map_key, sub)
        raise

    async def event_stream() -> AsyncIterator[bytes]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                # The client fell too far behind and its queue overflowed. Its
                # buffered deltas are now an incomplete history, so end the stream
                # instead of streaming a corrupt state — the browser reconnects and
                # the drop-snapshot-on-join above yields a fresh full resend.
                if sub.overflowed:
                    break
                # The ticket is only validated at connect; without this the loop
                # would stream forever with frozen capabilities. Re-check it on
                # every wake (message or keepalive, so at most one keepalive
                # interval past expiry) and close the stream once it expires —
                # the client reconnects with a freshly minted ticket.
                if principal_from_token(token) is None:
                    break
                try:
                    msg = await asyncio.wait_for(sub.queue.get(), timeout=_SSE_KEEPALIVE_INTERVAL)
                    yield f"data: {msg}\n\n".encode()
                except TimeoutError:
                    yield b": keepalive\n\n"
        finally:
            manager.unsubscribe(map_key, sub)

    headers = {
        # Apache buffers proxied responses by default; opt out so events flow
        # through immediately.
        "X-Accel-Buffering": "no",
        "Cache-Control": "no-cache, no-store",
    }
    return SseResponse(event_stream(), headers=headers)
