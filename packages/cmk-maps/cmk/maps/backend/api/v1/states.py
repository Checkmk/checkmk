#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""State endpoints + Server-Sent Events for real-time updates."""

import asyncio
import gzip
import logging
import math
import time
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Annotated, cast, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.sse import EventSourceResponse

from cmk.fastapi.gui_session import Unavailable
from cmk.fastapi.sse import EventStream, SentEvent
from cmk.maps.backend.api.v1.connections import auth_user_scope, build_topology_response
from cmk.maps.backend.api.v1.deps import (
    charge,
    get_current_user,
    get_map_owner,
    get_map_viewer,
    GuiAuthDep,
    rate_limited_map_read,
    registered_map,
    resolve_auth_user,
    SessionCookieDep,
)
from cmk.maps.backend.api.v1.types import MapName
from cmk.maps.backend.connections.base import ServiceMatchRow, ServiceRow
from cmk.maps.backend.core.auth import GuiAuth, Principal
from cmk.maps.backend.core.config import settings
from cmk.maps.backend.core.ratelimit import (
    kept_states_limiter,
    rest_read_limiter,
    sse_stream_limiter,
    ws_connect_limiter,
)
from cmk.maps.backend.core.single_flight import SingleFlight
from cmk.maps.backend.core.sse import manager, Subscriber
from cmk.maps.backend.core.ttl_cache import TtlCache
from cmk.maps.backend.integrations.checkmk import FolderScope, resolve_folder_scope
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
    MapSavedMessage,
    StateUpdateMessage,
    StreamedMapStates,
    StreamMessage,
    StreamTakenMessage,
    TopologyUpdateMessage,
)
from cmk.maps.backend.schemas.topology import TopologyNode
from cmk.maps.backend.services import map_service, settings_service, state_service
from cmk.maps.backend.services.map_service import LinkSource
from cmk.maps.shared.config_vars import MAX_STATE_REFRESH_INTERVAL

logger = logging.getLogger(__name__)

router = APIRouter()

MAP_EVENTS = EventStream(StreamMessage)


# Shared broadcast task per active map — avoids O(n²) fetch × broadcast.
# Without this every connected client would independently fetch the topology
# + states and push to all clients.
_broadcast_tasks: dict[str, asyncio.Task[None]] = {}
# Last dead-sites list pushed per (map, subscriber-group): a federation site
# dying/recovering must reach clients even when no node-level delta exists.
_dead_sites_snapshots: dict[tuple[str, str | None], list[str]] = {}


@dataclass
class _Fetched:
    gzipped: bytes
    objects: int
    # Registering a map anew replaces its config, so states of the old one
    # differ by it.
    config: MapConfig
    # When the query began, so a lone poller gets no states older than an interval.
    fetched_at: float
    polled: bool = False


type _FetchKey = tuple[str, str | None]


@dataclass
class _Flight:
    """A fetch that polls and the map's stream share."""

    states: MapStates
    fetched_at: float
    kept: _Fetched | None = None


# About 60 MB as JSON. A map with more objects than that alone is fetched per poll.
_FETCHED_MAX_OBJECTS = 100_000

# The latest states per (map, subscriber group), so the viewers that poll share
# one fetch per interval with each other and with the map's stream.
_fetched: TtlCache[_FetchKey, _Fetched] = TtlCache(
    maxsize=256,
    weigh=lambda fetched: fetched.objects,
    maxweight=_FETCHED_MAX_OBJECTS,
    expire_after=MAX_STATE_REFRESH_INTERVAL,
)
# The fetch under way per (map, subscriber group). Keyed by the config's identity
# too, so a poll after the map was registered anew does not get what a fetch of
# its old config brings.
_fetches: SingleFlight[tuple[str, str | None, int], _Flight] = SingleFlight()


@dataclass(frozen=True)
class _Topology:
    config: MapConfig
    nodes: list[TopologyNode]


type _TopologyKey = tuple[str, str | None]

# The latest topology per (flow map, auth user), so a new stream and a client
# without one get what the map's stream fetched in this interval.
_topologies: TtlCache[_TopologyKey, _Topology] = TtlCache(
    maxsize=256,
    weigh=lambda topology: sum(1 + len(node.services) for node in topology.nodes),
    maxweight=_FETCHED_MAX_OBJECTS,
    expire_after=MAX_STATE_REFRESH_INTERVAL,
)
_topology_fetches: SingleFlight[tuple[str, str | None, int], list[TopologyNode] | None] = (
    SingleFlight()
)

# What the SPA names a browser tab by (cmk-ui-library's randomId()).
_TAB_ID_PATTERN = r"^[-a-z0-9]{16}$"

# How often an open stream asks whether its session still holds. The answer is
# cached, so the GUI is asked again only once it has expired.
_SESSION_RECHECK_INTERVAL = 30.0
# Each proxy in front of the daemon notices a closed browser tab only when it
# writes, so an idle stream is written to on this beat.
_KEEPALIVE_INTERVAL = 5.0
_KEEPALIVE: SentEvent[StreamMessage] = SentEvent(comment="ping")


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
) -> StateUpdateMessage:
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
    )


def _map_key(owner: str, name: str) -> str:
    """Opaque per-stream key isolating a map by its MAP owner + name, so two
    users' same-named maps get separate cache entries, broadcast loops, and
    snapshots. NUL can't appear in either part (name is pattern-validated)."""
    return f"{owner}\x00{name}"


@dataclass(frozen=True)
class _Audience:
    auth_user: str | None
    # Only a foldertree map renders the Setup folders the user may read, which the
    # monitoring scope does not cover: a see-all guest shares auth_user=None with
    # an admin but sees fewer folders.
    folder_scope: FolderScope | None

    @property
    def group_key(self) -> str | None:
        if self.folder_scope is None:
            return self.auth_user
        # NUL for a see-all user, as no user name holds it, while "None" is one.
        user = "\x00" if self.auth_user is None else self.auth_user
        return f"{user}\x00{self.folder_scope.key}"


def _audience(user: Principal, cfg: MapConfig) -> _Audience:
    return _Audience(
        resolve_auth_user(user),
        resolve_folder_scope(user) if cfg.view.type == "foldertree" else None,
    )


def _remember(
    key: _FetchKey, owner: str, cfg: MapConfig, states: MapStates, *, fetched_at: float
) -> _Fetched:
    tree_hosts = states.folder_tree.host_count if states.folder_tree is not None else 0
    # Compressed once here rather than by the middleware for every poll.
    fetched = _Fetched(
        gzip.compress(states.model_dump_json().encode(), compresslevel=1, mtime=0),
        len(states.states) + tree_hosts,
        cfg,
        fetched_at,
    )
    if fetched.objects <= _FETCHED_MAX_OBJECTS and map_service.get_map(owner, cfg.name) is cfg:
        _fetched.set(key, fetched)
    return fetched


def _was_polled(key: _FetchKey) -> bool:
    return (fetched := _fetched.get(key, ttl=math.inf)) is not None and fetched.polled


async def _group_states(
    key: _FetchKey,
    owner: str,
    cfg: MapConfig,
    auth_user: str | None,
    folder_scope: FolderScope | None,
    links: LinkSource,
) -> _Flight:
    async def fetch() -> _Flight:
        fetched_at = time.monotonic()
        states = await state_service.get_map_states(
            cfg,
            auth_user=auth_user,
            folder_scope=folder_scope,
            map_owner=owner,
            links=links,
        )
        return _Flight(states, fetched_at)

    return await _fetches.run((*key, id(cfg)), fetch)


def _kept(key: _FetchKey, owner: str, cfg: MapConfig, flight: _Flight) -> _Fetched:
    """The fetch as kept for polls, compressed once for all that shared it."""
    if flight.kept is None:
        flight.kept = _remember(key, owner, cfg, flight.states, fetched_at=flight.fetched_at)
    return flight.kept


async def _shared_states(
    cfg: MapConfig, user: Principal, audience: _Audience, links: LinkSource
) -> bytes:
    """The states of the current interval as gzip, fetched once for everyone polling them."""
    owner = user.map_key_owner
    key = (_map_key(owner, cfg.name), audience.group_key)
    ttl = settings_service.get_effective_state_refresh_interval()
    fetched = _fetched.get(key, ttl=ttl)
    if fetched is None or fetched.config is not cfg or time.monotonic() - fetched.fetched_at >= ttl:
        flight = await _group_states(
            key, owner, cfg, audience.auth_user, audience.folder_scope, links
        )
        fetched = _kept(key, owner, cfg, flight)
    else:
        # The read budget spares Livestatus, which states kept already do not ask.
        rest_read_limiter.refund(user.name)
        charge(kept_states_limiter, user.name)
    fetched.polled = True
    return fetched.gzipped


async def _group_topology(
    map_key: str, cfg: MapConfig, auth_user: str | None, *, fresh: bool
) -> list[TopologyNode] | None:
    """The topology of the map for the group, fetched once per interval unless ``fresh``."""
    key = (map_key, auth_user)
    if not fresh:
        ttl = settings_service.get_effective_state_refresh_interval()
        if (kept := _topologies.get(key, ttl=ttl)) is not None and kept.config is cfg:
            return kept.nodes

    async def fetch() -> list[TopologyNode] | None:
        nodes = await _fetch_topology_for_user(cfg, auth_user)
        if nodes is not None:
            _topologies.set(key, _Topology(cfg, nodes))
        return nodes

    return await _topology_fetches.run((*key, id(cfg)), fetch)


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
    # A newcomer gets what the group's stream fetched in this interval.
    nodes = await _group_topology(map_key, cfg, auth_user, fresh=store)
    if nodes is None:
        return
    delta = state_service.compute_topology_delta(
        map_key, auth_user, nodes, force_full=force_full, store=store
    )
    if not (force_full or delta.added or delta.changed or delta.removed or delta.timing):
        return
    # ``map`` carries the real map name (the SPA matches messages by it); the
    # snapshot/push key is the owner-qualified map key.
    msg = TopologyUpdateMessage(map=cfg.name, delta=delta)
    manager.push(map_key, targets, MAP_EVENTS.encode(msg))


async def _broadcast_loop(map_key: str, links: LinkSource) -> None:
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
            # Read fresh each tick so System-Settings changes apply without
            # restarting the backend.
            interval = settings_service.get_effective_state_refresh_interval()
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
                        key = (map_key, group_key)
                        flight = await _group_states(
                            key, owner, cfg, auth_user, rep.folder_scope, links
                        )
                        states = flight.states
                        # Only for a group that polled since the last tick, so the
                        # cache holds nothing for maps everyone streams.
                        if _was_polled(key):
                            _kept(key, owner, cfg, flight)
                        else:
                            _fetched.pop(key)
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
                            manager.push(map_key, established, MAP_EVENTS.encode(msg))
                        if newcomers:
                            full_ft = (
                                FolderTreeDelta(full=True, tree=states.folder_tree)
                                if cfg.view.type == "foldertree"
                                else None
                            )
                            full_msg = _build_states_msg(
                                name, states, states.states, [], True, [], full_ft
                            )
                            manager.push(map_key, newcomers, MAP_EVENTS.encode(full_msg))
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
            await asyncio.sleep(interval)
    finally:
        _broadcast_tasks.pop(map_key, None)
        state_service.drop_topology_snapshot(map_key)
        state_service.drop_states_snapshot(map_key)
        state_service.drop_map_snapshots(_dead_sites_snapshots, map_key)
        _fetched.invalidate(lambda key: key[0] == map_key)
        logger.debug("Broadcast loop stopped for map '%(map)s'", {"map": name})


def tell_map_saved(owner: str, name: str, sig: str) -> None:
    """Tell every open view of the map which version is saved."""
    map_key = _map_key(owner, name)
    if subscribers := manager.get_subscribers(map_key):
        manager.push(map_key, subscribers, MAP_EVENTS.encode(MapSavedMessage(map=name, sig=sig)))


_RADAR_FILTERS: set[str] = {"hostgroup", "servicegroup", "all_hosts", "all_services"}


async def map_states_response(
    cfg: MapConfig, current_user: Principal, links: LinkSource
) -> Response:
    """The full states of ``cfg`` as the caller may see them, pre-dumped."""
    audience = _audience(current_user, cfg)
    states = await state_service.get_map_states(
        cfg,
        auth_user=audience.auth_user,
        folder_scope=audience.folder_scope,
        map_owner=current_user.map_key_owner,
        links=links,
    )
    return Response(content=states.model_dump_json(), media_type="application/json")


@dataclass(frozen=True)
class ViewPreview:
    """Unsaved view settings the settings preview shows states for."""

    radar_filter: str | None
    radar_filter_value: str | None
    ft_override: bool
    ft_root_folder: str
    ft_show_empty_folders: bool
    ft_only_hard_states: bool
    ft_sites: list[str]

    @property
    def overrides(self) -> bool:
        return self.radar_filter is not None or self.ft_override

    def apply(self, cfg: MapConfig) -> MapConfig:
        # Settings-preview override for radar maps. Both query params arrive
        # together so we never mix disk-state filter with a half-edited override.
        if (
            cfg.view.type == "radar"
            and self.radar_filter is not None
            and self.radar_filter_value is not None
            and self.radar_filter in _RADAR_FILTERS
        ):
            cfg = cfg.model_copy(
                update={
                    "view": RadarView(
                        filter=cast(
                            Literal["hostgroup", "servicegroup", "all_hosts", "all_services"],
                            self.radar_filter,
                        ),
                        filter_value=self.radar_filter_value,
                    )
                }
            )
        # Settings-preview override for foldertree maps: only the server-side view
        # fields (the others are mirrored client-side and need no requery). Gated on
        # an explicit flag so an empty root_folder reads as "(all)" not "unset".
        # problems_only is forced off so the server never prunes healthy nodes — the
        # client filters it reactively, so toggling it in the preview works both ways
        # without a per-toggle tree rebuild.
        if self.ft_override and isinstance(cfg.view, FolderTreeView):
            cfg = cfg.model_copy(
                update={
                    "view": cfg.view.model_copy(
                        update={
                            "root_folder": self.ft_root_folder,
                            "show_empty_folders": self.ft_show_empty_folders,
                            "only_hard_states": self.ft_only_hard_states,
                            "sites": self.ft_sites,
                            "problems_only": False,
                        }
                    )
                }
            )
        return cfg


def view_preview(
    current_user: Annotated[Principal, Depends(get_current_user)],
    owner: Annotated[str | None, Depends(get_map_owner)],
    radar_filter: str | None = None,
    radar_filter_value: str | None = None,
    ft_override: bool = False,
    ft_root_folder: str = "",
    ft_show_empty_folders: bool = True,
    ft_only_hard_states: bool = False,
    ft_sites: list[str] = Query(default_factory=list),
) -> ViewPreview:
    preview = ViewPreview(
        radar_filter=radar_filter,
        radar_filter_value=radar_filter_value,
        ft_override=ft_override,
        ft_root_folder=ft_root_folder,
        ft_show_empty_folders=ft_show_empty_folders,
        ft_only_hard_states=ft_only_hard_states,
        ft_sites=ft_sites,
    )
    # The settings preview is the only sender, and only who may save the map opens it.
    if preview.overrides and not (owner is not None and current_user.may_preview(owner)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a user who may save the map previews its unsaved view",
        )
    return preview


# Returns a pre-dumped Response (passed through untouched) instead of a model:
# skips FastAPI's second full re-validation, which dominated initial load on
# 100k+-host maps. response_model stays for the OpenAPI schema (api.ts codegen).
@router.get("/maps/{name}/states", response_model=MapStates)
async def get_map_states(
    name: MapName,
    request: Request,
    auth: GuiAuthDep,
    current_user: Principal = Depends(rate_limited_map_read),
    preview: ViewPreview = Depends(view_preview),
) -> Response:
    cfg = registered_map(current_user, name)
    if preview.overrides:
        return await map_states_response(preview.apply(cfg), current_user, auth)
    body = await _shared_states(cfg, current_user, _audience(current_user, cfg), auth)
    if "gzip" not in request.headers.get("accept-encoding", ""):
        return Response(
            content=gzip.decompress(body),
            media_type="application/json",
            headers={"Vary": "Accept-Encoding"},
        )
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Encoding": "gzip", "Vary": "Accept-Encoding"},
    )


@router.get("/maps/{name}/topology", response_model=list[TopologyNode])
async def get_map_topology(
    name: MapName, current_user: Principal = Depends(rate_limited_map_read)
) -> list[TopologyNode]:
    """The topology of a flow map as its stream carries it, for a client without the stream."""
    cfg = registered_map(current_user, name)
    if not isinstance(cfg.view, FlowView):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' is no flow map"
        )
    nodes = await _group_topology(
        _map_key(current_user.map_key_owner, cfg.name),
        cfg,
        resolve_auth_user(current_user),
        fresh=False,
    )
    if nodes is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The topology is unavailable"
        )
    return nodes


@router.get("/maps/{name}/folder-host-services", response_model=list[FolderHostService])
async def get_folder_host_services(
    name: MapName,
    host: str = Query(..., description="Host name to fetch services for"),
    current_user: Principal = Depends(rate_limited_map_read),
) -> list[FolderHostService]:
    """Lazily fetch a single host's services for a foldertree map.

    Only invoked when an operator expands a host in the tree/map — a single
    host-scoped Livestatus query — so the map scales to environments with
    millions of hosts (services are never pushed eagerly over SSE).
    """
    cfg = registered_map(current_user, name)
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
    current_user: Principal = Depends(rate_limited_map_read),
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

    cfg = registered_map(current_user, name)
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


@dataclass(frozen=True)
class StreamSubscription:
    subscriber: Subscriber
    name: str
    user: Principal
    auth: GuiAuth
    # The repr lands in crash reports, which redact by variable name only.
    session_cookie: str = field(repr=False)


async def session_still_holds(subscription: StreamSubscription) -> bool:
    """Whether the session still gets the user, with the scope, the stream started with.

    Without a verdict of the GUI the stream goes on and asks again next time:
    closing it would only make the browser reconnect against the same GUI.
    """
    now = time.monotonic()
    match await subscription.auth.principal(subscription.session_cookie, now=now):
        case Principal() as current:
            pass
        case Unavailable():
            return True
        case _:
            return False
    match await subscription.auth.map_owner(current, subscription.name, now=now):
        case str() as owner:
            return current.viewing(owner, subscription.name) == subscription.user
        case Unavailable():
            return True
        case _:
            return False


async def _connect_budget(current_user: Principal = Depends(get_current_user)) -> Principal:
    # Keyed by the user: behind the site's proxies every client arrives from the
    # same address, so an IP key would share one budget site-wide.
    if ws_connect_limiter.is_blocked(current_user.name):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limited")
    ws_connect_limiter.record(current_user.name)
    return current_user


@dataclass
class _TabStream:
    subscriber: Subscriber
    holds_slot: bool = True


# The stream each browser tab holds, by (user, tab). A tab that tries the stream
# again while polling opens a probe and then the stream; the probe's slot is only
# freed once a proxy noticed it closed, so the stream takes it over instead.
_tab_streams: dict[tuple[str, str], _TabStream] = {}


def _take_slot(user: str, tab: str | None) -> None:
    if tab is not None and (held := _tab_streams.get((user, tab))) is not None:
        held.holds_slot = False
        queue = held.subscriber.queue
        # What it still had to send is of no use to a page that has to name its tab
        # anew, and a full queue would leave no room to tell it.
        with suppress(asyncio.QueueEmpty, asyncio.QueueShutDown):
            while True:
                queue.get_nowait()
        with suppress(asyncio.QueueShutDown):
            queue.put_nowait(MAP_EVENTS.encode(StreamTakenMessage()))
        queue.shutdown()
    elif not sse_stream_limiter.try_acquire(user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many concurrent streams"
        )


async def _subscribe_to_stream(
    name: MapName,
    cookie: SessionCookieDep,
    auth: GuiAuthDep,
    # Before the viewer: resolving the map asks the GUI, which the budget is there to spare.
    _budget: Principal = Depends(_connect_budget),
    user: Principal = Depends(get_map_viewer),
    tab: Annotated[str | None, Query(pattern=_TAB_ID_PATTERN)] = None,
) -> AsyncIterator[StreamSubscription]:
    # Owner = the map's REAL owner as the GUI named it for the user, never a
    # client value — so all viewers of a published map share one broadcast loop,
    # while a private map stays in its owner's namespace and no user can address
    # another's stream.
    cfg = registered_map(user, name)
    owner = user.map_key_owner
    map_key = _map_key(owner, name)

    audience = _audience(user, cfg)

    _take_slot(user.name, tab)
    sub = manager.subscribe(
        map_key,
        audience.auth_user,
        folder_scope=audience.folder_scope,
        group_key=audience.group_key,
    )
    stream = _TabStream(sub)
    if tab is not None:
        _tab_streams[(user.name, tab)] = stream
    try:
        # A new subscriber must not diverge from its REST first paint on anything
        # that changed before it joined (the group snapshot already absorbed those,
        # so a plain delta would skip them). It is flagged ``needs_full`` (default
        # on a fresh Subscriber), and the broadcast loop sends it a full built from
        # the same fetch — re-fulling only this client, not the whole group.
        if map_key not in _broadcast_tasks or _broadcast_tasks[map_key].done():
            _broadcast_tasks[map_key] = asyncio.create_task(_broadcast_loop(map_key, auth))

        # First-paint topology for Flow Maps so the client doesn't wait a full
        # broadcast tick before the initial render. ``store=False`` keeps the shared
        # snapshot intact, so the group's already-connected viewers keep getting
        # deltas (topology deltas are convergent upserts, so this client reconverges
        # from the next tick's group delta on top of this full) — no group re-full.
        if cfg.view.type == "flow":
            await _push_topology_to(
                cfg, map_key, audience.auth_user, [sub], force_full=True, store=False
            )

        yield StreamSubscription(
            subscriber=sub, name=name, user=user, auth=auth, session_cookie=cookie
        )
    finally:
        manager.unsubscribe(map_key, sub)
        if tab is not None and _tab_streams.get((user.name, tab)) is stream:
            del _tab_streams[(user.name, tab)]
        if stream.holds_slot:
            sse_stream_limiter.release(user.name)


@router.get(
    "/sse/maps/{name}",
    response_class=EventSourceResponse,
    response_description="The state and topology updates of the map.",
)
async def sse_map_states(
    request: Request,
    subscription: StreamSubscription = Depends(_subscribe_to_stream),
) -> AsyncIterator[SentEvent[StreamMessage]]:
    """SSE endpoint streaming state + topology updates for a map.

    Authenticated by the GUI session cookie like every other request. The
    session is checked again while the stream is open, so a stream ends soon
    after its user logged out, was locked, or lost the map.
    """
    sub = subscription.subscriber
    next_check = time.monotonic() + _SESSION_RECHECK_INTERVAL
    # The browser takes the stream as open with its first bytes, which the
    # compression holds back until there is an event to send.
    yield SentEvent(comment="open")
    while True:
        if await request.is_disconnected():
            break
        # The client fell too far behind and its queue overflowed. Its
        # buffered deltas are now an incomplete history, so end the stream
        # instead of streaming a corrupt state — the browser reconnects and
        # gets a full resend as a new subscriber.
        if sub.overflowed:
            break
        if time.monotonic() >= next_check:
            # A changed scope ends the stream too: the browser reconnects and
            # joins the subscriber group of the new one.
            if not await session_still_holds(subscription):
                break
            next_check = time.monotonic() + _SESSION_RECHECK_INTERVAL
        try:
            event = await asyncio.wait_for(sub.queue.get(), timeout=_KEEPALIVE_INTERVAL)
        except TimeoutError:
            event = _KEEPALIVE
        except asyncio.QueueShutDown:
            break
        yield event
