#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Aggregate monitoring states for map objects."""

from __future__ import annotations

import asyncio
import gc
import logging
import time
from collections.abc import Collection, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from cmk.maps.backend.connections.base import FolderTreeData, GeoHost, ServiceRow
from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations.checkmk import FolderScope
from cmk.maps.backend.schemas.map import (
    FolderTreeView,
    MapConfig,
    MapElement,
    RadarView,
    WorldmapView,
)
from cmk.maps.backend.schemas.presentation import DataElement, PresentationView, ShapeElement
from cmk.maps.backend.schemas.state import (
    FolderHostService,
    FolderTreeDelta,
    FolderTreeNode,
    FolderTreeNodePatch,
    MapStates,
    ObjectState,
    ObjectTiming,
    ServicesSummary,
)
from cmk.maps.backend.schemas.topology import (
    ServiceTiming,
    TopologyDelta,
    TopologyNode,
    TopologyTiming,
)
from cmk.maps.backend.services.settings_service import get_daemon_runtime
from cmk.maps.shared.map_payload import ObjectType
from cmk.maps.shared.states import CRITICAL_STATES, SEVERITY_RANK, severity_rank


def sort_folder_services(services: list[FolderHostService]) -> None:
    """Order a foldertree host's services worst-state first, then alphabetical —
    the single ordering contract shared by the lazy expand and the search result
    so the same host's services don't reshuffle depending on how they loaded."""
    services.sort(key=lambda s: (-severity_rank(s.state), s.name.lower()))


_MONITORING_TYPES: frozenset[str] = frozenset(
    {"host", "service", "hostgroup", "servicegroup", "line", "graph"}
)
# Types that contribute to the worst-state roll-up of a map-link object.
# Includes map and aggregation so nested maps transitively show up in the
# parent map's status pill.
_MAP_AGGREGATION_TYPES: frozenset[str] = _MONITORING_TYPES | {"map", "aggregation"}

if TYPE_CHECKING:
    from cmk.maps.backend.connections.base import ConnectionBase

logger = logging.getLogger(__name__)

_connections: dict[str, ConnectionBase] = {}


def register_connection(connection_id: str, connection: ConnectionBase) -> None:
    _connections[connection_id] = connection


def unregister_connection(connection_id: str) -> None:
    _connections.pop(connection_id, None)


def get_connection(connection_id: str) -> ConnectionBase | None:
    return _connections.get(connection_id)


def list_connection_ids() -> list[str]:
    return list(_connections.keys())


async def get_map_states(
    cfg: MapConfig,
    auth_user: str | None = None,
    folder_scope: FolderScope | None = None,
) -> MapStates:
    """Fetch current states for all objects in a map.

    When *auth_user* is provided, Livestatus queries are scoped to that user's
    contact groups so they only see objects they are authorised for.
    *folder_scope* independently scopes a foldertree
    map's SETUP folder skeleton to the folders the user may read (see-all
    guests see all hosts but not all folder names) — distinct from *auth_user*.
    """
    connection_id = cfg.connection_id
    connection = get_connection(connection_id)

    if connection is None:
        logger.warning(
            "No connection registered for '%(connection_id)s'", {"connection_id": connection_id}
        )
        states = [
            ObjectState(object_id=obj.id, type=obj.type, state="PENDING") for obj in cfg.objects
        ]
        return MapStates(
            map_name=cfg.name,
            states=states,
            generated_at=time.time(),
            connection_ok=False,
            runtime=get_daemon_runtime(),
        )

    async def _run() -> MapStates:
        # Folder scope is set for every CMK request (admins included) so the
        # folder tree is filtered by SETUP read-permission; auth_user adds the
        # Livestatus host filter only for non-see-all monitoring users.
        if auth_user is not None:
            async with connection.with_auth_user(auth_user):
                return await _execute_map_states(cfg, connection, auth_user=auth_user)
        return await _execute_map_states(cfg, connection, auth_user=auth_user)

    async with connection.with_folder_scope(folder_scope):
        return await _run()


async def _derive_connection_ok(states: list[ObjectState], connection: ConnectionBase) -> bool:
    """Connection health from monitoring-object states.

    Non-monitoring types (image, textbox, map) always return PENDING without
    ``stale=True``, so they are excluded — the connection counts as down only
    when ALL monitoring queries raised (stale). Maps without monitoring
    objects ping the connection explicitly.
    """
    monitoring_states = [s for s in states if s.type in _MONITORING_TYPES]
    if monitoring_states:
        return not all(s.stale for s in monitoring_states)
    try:
        return await connection.is_available()
    except Exception:
        return False


async def _execute_map_states(
    cfg: MapConfig,
    connection: ConnectionBase,
    auth_user: str | None = None,
) -> MapStates:
    """Inner state-fetch implementation; must be called with auth context already set."""
    if cfg.view.type == "radar":
        return await _get_radar_states(cfg, connection)

    if cfg.view.type == "foldertree":
        return await _get_folder_tree_states(cfg, connection)

    if cfg.view.type == "presentation":
        return await _get_presentation_states(cfg, connection, auth_user=auth_user)

    # Inflate worldmap automap-source hosts into transient map objects so
    # the rest of the pipeline (state fetch, stream diffing, frontend
    # rendering) treats them like any other host. They are not persisted —
    # the MapConfig in map_service still holds only the user-curated set.
    objects = await inflate_auto_objects(cfg, connection)

    state_map = await _states_for_objects(
        objects,
        default_connection=connection,
        default_connection_id=cfg.connection_id,
        auth_user=auth_user,
        visited_maps=frozenset({cfg.name}),
    )
    states = list(state_map.values())

    connection_ok = await _derive_connection_ok(states, connection)

    return MapStates(
        map_name=cfg.name,
        states=states,
        generated_at=time.time(),
        connection_ok=connection_ok,
        runtime=get_daemon_runtime(),
    )


_AUTO_PREFIX = "auto:"


def _names_or_filter(names: list[str]) -> str:
    # Drop names carrying a newline OR a backslash: this runtime-built filter
    # skips the schema-layer normalize_object_filter, and get_dyngroup_state
    # later un-escapes ``\n`` → a real newline. A literal backslash-n in a name
    # would therefore smuggle in extra Livestatus header lines (Stats:/Filter:).
    # Real host names contain neither character.
    safe = [n for n in names if "\n" not in n and "\\" not in n]
    lines = "".join(f"Filter: name = {n}\n" for n in safe)
    return lines + (f"Or: {len(safe)}\n" if len(safe) > 1 else "")


async def inflate_auto_objects(cfg: MapConfig, connection: ConnectionBase) -> list[MapElement]:
    """Resolve a worldmap's automap hosts and geo "bundles".

    ``auto_source`` appends every geo host as a transient marker (persisted
    objects win on name clash). Location bundles additionally re-match hosts at
    their coordinate so new hosts there auto-join; both bundle kinds suppress
    their members' individual markers.
    """
    view = cfg.view
    if not isinstance(view, WorldmapView):
        return cfg.objects
    has_location_bundle = any(o.bundle_kind == "location" for o in cfg.objects)
    if view.auto_source is None and not has_location_bundle:
        return cfg.objects

    # Only auto_source maps fetch the (potentially huge) geo-host list; a
    # location bundle then auto-joins from it. Without auto_source we skip the
    # fetch and the bundle falls back to its persisted member baseline.
    geo_hosts: list[GeoHost] = []
    if view.auto_source is not None:
        group_type = view.auto_source if view.auto_source != "all_hosts" else None
        try:
            geo_hosts = await connection.get_hosts_with_geo(
                group_type=group_type, group_name=view.auto_filter_value or None
            )
        except Exception:
            logger.warning(
                "Failed to fetch geo hosts for map %(map)s", {"map": cfg.name}, exc_info=True
            )

    existing_host_names = {o.host_name for o in cfg.objects if o.host_name}
    for o in cfg.objects:
        if o.bundle_kind and o.bundle_hosts:
            existing_host_names.update(o.bundle_hosts)

    inflated: list[MapElement] = []
    for o in cfg.objects:
        if o.bundle_kind == "location" and o.lat is not None and o.lng is not None:
            prec = o.bundle_precision if o.bundle_precision is not None else 5
            at_coord = [
                h["name"]
                for h in geo_hosts
                if round(h["lat"], prec) == round(o.lat, prec)
                and round(h["lng"], prec) == round(o.lng, prec)
            ]
            members = sorted(set(at_coord) | set(o.bundle_hosts or []))
            existing_host_names.update(members)
            inflated.append(
                o.model_copy(
                    update={
                        "bundle_hosts": members,
                        "object_filter": _names_or_filter(members) if members else o.object_filter,
                    }
                )
            )
        else:
            inflated.append(o)

    if view.auto_source is not None:
        for h in geo_hosts:
            if h["name"] in existing_host_names:
                continue
            inflated.append(
                MapElement(
                    id=f"{_AUTO_PREFIX}{h['name']}",
                    type="host",
                    host_name=h["name"],
                    lat=h["lat"],
                    lng=h["lng"],
                )
            )
    return inflated


async def _states_for_objects(
    objects: list[MapElement],
    *,
    default_connection: ConnectionBase,
    default_connection_id: str,
    auth_user: str | None = None,
    map_cfg_cache: dict[str, MapConfig | None] | None = None,
    visited_maps: frozenset[str] = frozenset(),
) -> dict[str, ObjectState]:
    """Run the batched state fetch once per distinct connection, then merge.

    NagVis maps allow ``backend_id`` per object so a single map can mix
    monitoring sources (two CMK sites, …). We honour the
    same contract: an object's ``connection_id`` overrides the map default.
    Objects sharing a connection are still batched together — only the
    cross-connection split adds round-trips, which run in parallel.
    """
    if map_cfg_cache is None:
        map_cfg_cache = {}

    groups: dict[str, list[MapElement]] = {}
    for obj in objects:
        cid = obj.connection_id or default_connection_id
        groups.setdefault(cid, []).append(obj)

    async def _run(cid: str, group_objs: list[MapElement]) -> dict[str, ObjectState]:
        conn = default_connection if cid == default_connection_id else get_connection(cid)
        if conn is None:
            return {
                obj.id: ObjectState(object_id=obj.id, type=obj.type, state="PENDING", stale=True)
                for obj in group_objs
            }
        return await _get_map_states_batched(
            conn,
            group_objs,
            auth_user=auth_user,
            map_cfg_cache=map_cfg_cache,
            _visited_maps=visited_maps,
        )

    if len(groups) == 1:
        cid, group_objs = next(iter(groups.items()))
        return await _run(cid, group_objs)

    results = await asyncio.gather(*[_run(cid, objs) for cid, objs in groups.items()])
    merged: dict[str, ObjectState] = {}
    for r in results:
        merged.update(r)
    return merged


@dataclass
class _MapElementBins:
    """Map objects split by the kind of state query each needs."""

    hosts_soft: list[MapElement] = field(default_factory=list)
    hosts_hard: list[MapElement] = field(default_factory=list)
    svcs_soft: list[MapElement] = field(default_factory=list)
    svcs_hard: list[MapElement] = field(default_factory=list)
    lines: list[MapElement] = field(default_factory=list)
    map_objects: list[MapElement] = field(default_factory=list)
    others: list[MapElement] = field(default_factory=list)


def _bin_map_elements(objects: list[MapElement]) -> _MapElementBins:
    """Split map objects into per-query-kind bins (hosts vs services vs …).

    Hosts and services are further split by ``only_hard_states`` so each batch
    query carries a uniform ``only_hard`` flag. ``graph`` objects piggyback on
    the host/service batches depending on whether they target a service.
    """
    bins = _MapElementBins()
    for obj in objects:
        if obj.type == "host" and obj.host_name:
            (bins.hosts_hard if obj.only_hard_states else bins.hosts_soft).append(obj)
        elif obj.type == "service" and obj.host_name and obj.service_description:
            (bins.svcs_hard if obj.only_hard_states else bins.svcs_soft).append(obj)
        elif obj.type == "graph" and obj.host_name and obj.service_description:
            bins.svcs_soft.append(obj)
        elif obj.type == "graph" and obj.host_name:
            bins.hosts_soft.append(obj)
        elif obj.type == "line":
            bins.lines.append(obj)
        elif obj.type == "map" and obj.map_name:
            bins.map_objects.append(obj)
        elif obj.type == "aggregation":
            continue  # resolved GUI-side, not by the daemon
        else:
            bins.others.append(obj)
    return bins


async def _resolve_host_states(
    connection: ConnectionBase,
    hosts_soft: list[MapElement],
    hosts_hard: list[MapElement],
    auth_user: str | None,
    results: dict[str, ObjectState],
) -> None:
    """Batch-fetch host states, then enrich with service summaries and
    ``recognize_services`` aggregation. Writes resolved states into *results*."""
    for host_group, only_hard in [(hosts_soft, False), (hosts_hard, True)]:
        if not host_group:
            continue
        batch_ok = True
        try:
            batch = await connection.get_hosts_states(
                [o.host_name for o in host_group if o.host_name is not None],
                only_hard=only_hard,
            )
        except Exception:
            logger.warning(
                "Batch host state query failed (only_hard=%(only_hard)s)",
                {"only_hard": only_hard},
                exc_info=True,
            )
            batch = {}
            batch_ok = False
        for obj in host_group:
            assert obj.host_name is not None
            if batch_ok and obj.host_name not in batch:
                # Permission-filtered batches return only the hosts a non-admin
                # user is allowed to see; for that user the missing entry is a
                # permission denial. For admin/SSO-admin context (auth_user is
                # None) the host is *actually* not present in monitoring data.
                state_value = "NO_PERMISSION" if auth_user is not None else "NOT_FOUND"
                results[obj.id] = ObjectState(object_id=obj.id, type="host", state=state_value)
            else:
                raw = batch.get(obj.host_name)
                s = (
                    ObjectState(**{**raw.model_dump(), "object_id": obj.id})
                    if raw is not None
                    else ObjectState(object_id=obj.id, type="host", state="PENDING", stale=True)
                )
                results[obj.id] = s

    host_objs = hosts_soft + hosts_hard
    summary_hosts = sorted(
        {
            o.host_name
            for o in host_objs
            if o.host_name is not None
            and results.get(o.id) is not None
            and results[o.id].state not in ("NO_PERMISSION", "NOT_FOUND")
        }
    )
    rs_objs = [
        o
        for o in host_objs
        if o.recognize_services
        and results.get(o.id) is not None
        and results[o.id].state != "NO_PERMISSION"
    ]
    rs_names = list({o.host_name for o in rs_objs if o.host_name is not None})

    # Run summary + recognize_services service-batch in parallel — both depend on
    # the host-state batch above but neither depends on the other.
    summary_task: asyncio.Task[dict[str, ServicesSummary]] | None = (
        asyncio.create_task(connection.get_services_summary(summary_hosts))
        if summary_hosts
        else None
    )
    rs_task: asyncio.Task[dict[str, list[ServiceRow]]] | None = (
        asyncio.create_task(connection.get_hosts_services_batch(rs_names)) if rs_objs else None
    )

    if summary_task is not None:
        try:
            summary_batch = await summary_task
        except Exception:
            logger.warning("Services-summary query failed", exc_info=True)
            summary_batch = {}
        for obj in host_objs:
            if obj.host_name is None:
                continue
            existing = results.get(obj.id)
            if existing is None:
                continue
            summary = summary_batch.get(obj.host_name)
            if summary is not None:
                results[obj.id] = existing.model_copy(update={"services_summary": summary})

    if rs_task is not None:
        try:
            rs_svc_batch = await rs_task
        except Exception:
            logger.warning("Batch host-services query failed", exc_info=True)
            rs_svc_batch = {}
        for obj in rs_objs:
            assert obj.host_name is not None
            results[obj.id] = _aggregate_host_with_services_from_data(
                results[obj.id],
                rs_svc_batch.get(obj.host_name, []),
            )


async def _resolve_service_states(
    connection: ConnectionBase,
    svcs_soft: list[MapElement],
    svcs_hard: list[MapElement],
    auth_user: str | None,
    results: dict[str, ObjectState],
) -> None:
    """Batch-fetch service states (soft and hard groups) into *results*."""
    for svc_group, only_hard in [(svcs_soft, False), (svcs_hard, True)]:
        if not svc_group:
            continue
        pairs = [
            (o.host_name, o.service_description)
            for o in svc_group
            if o.host_name is not None and o.service_description is not None
        ]
        batch_ok = True
        try:
            svc_batch = await connection.get_services_states(pairs, only_hard=only_hard)
        except Exception:
            logger.warning(
                "Batch service state query failed (only_hard=%(only_hard)s)",
                {"only_hard": only_hard},
                exc_info=True,
            )
            svc_batch = {}
            batch_ok = False
        for obj in svc_group:
            assert obj.host_name is not None and obj.service_description is not None
            key = (obj.host_name, obj.service_description)
            if batch_ok and key not in svc_batch:
                state_value = "NO_PERMISSION" if auth_user is not None else "NOT_FOUND"
                results[obj.id] = ObjectState(object_id=obj.id, type="service", state=state_value)
            else:
                raw = svc_batch.get(key)
                s = (
                    ObjectState(**{**raw.model_dump(), "object_id": obj.id})
                    if raw is not None
                    else ObjectState(object_id=obj.id, type="service", state="PENDING", stale=True)
                )
                results[obj.id] = s


async def _resolve_individual_states(
    connection: ConnectionBase,
    objects: list[MapElement],
    results: dict[str, ObjectState],
) -> None:
    """Resolve objects that have no batch query (lines and everything else)
    one-by-one, in parallel, into *results*."""
    individual = [_get_object_state(connection, obj) for obj in objects]
    for state in await asyncio.gather(*individual):
        results[state.object_id] = state


async def _resolve_map_link_states(
    map_objects: list[MapElement],
    auth_user: str | None,
    map_cfg_cache: dict[str, MapConfig | None],
    visited_maps: frozenset[str],
    results: dict[str, ObjectState],
) -> None:
    """Aggregate each map-link object to the worst state of the map it
    references, recursing into nested maps while guarding against cycles."""
    if not map_objects:
        return
    from cmk.maps.backend.services import map_service

    # Load each unique referenced map once (avoid N reads for N map-link objects).
    map_states: dict[str, dict[str, ObjectState]] = {}
    for map_name in {o.map_name for o in map_objects if o.map_name}:
        if map_name not in map_cfg_cache:
            # Nested map-link: referenced by name only (no owner). get_map's
            # name fallback resolves it against any registered owner.
            map_cfg_cache[map_name] = map_service.get_map("", map_name)
        ref_cfg = map_cfg_cache[map_name]
        if ref_cfg is None:
            continue
        ref_backend = get_connection(ref_cfg.connection_id)
        if ref_backend is None:
            continue
        # Include nested map-objects in the recursion as long as they
        # don't form a cycle — otherwise a map with only nested links
        # would aggregate to PENDING even when its leaves have real states.
        child_visited = visited_maps | {map_name}
        included_objs = [
            o
            for o in ref_cfg.objects
            if o.type != "map" or (o.map_name and o.map_name not in child_visited)
        ]
        try:
            map_states[map_name] = await _states_for_objects(
                included_objs,
                default_connection=ref_backend,
                default_connection_id=ref_cfg.connection_id,
                auth_user=auth_user,
                map_cfg_cache=map_cfg_cache,
                visited_maps=child_visited,
            )
        except Exception as exc:
            # A broken nested map-link shouldn't sink the parent map, but
            # the failure is otherwise invisible — surface it at debug level.
            logger.debug("Nested map-link state aggregation failed: %(error)s", {"error": exc})
    for obj in map_objects:
        assert obj.map_name is not None
        sub = map_states.get(obj.map_name) or {}
        mon = [s for s in sub.values() if s.type in _MAP_AGGREGATION_TYPES]
        if mon:
            real = [s for s in mon if s.state != "NO_PERMISSION"]
            if not real:
                results[obj.id] = ObjectState(object_id=obj.id, type="map", state="NO_PERMISSION")
            else:
                worst = max(real, key=lambda s: SEVERITY_RANK.get(s.state, 0))
                results[obj.id] = ObjectState(object_id=obj.id, type="map", state=worst.state)
        else:
            results[obj.id] = ObjectState(object_id=obj.id, type="map", state="PENDING")


async def _get_map_states_batched(
    connection: ConnectionBase,
    objects: list[MapElement],
    auth_user: str | None = None,
    map_cfg_cache: dict[str, MapConfig | None] | None = None,
    _visited_maps: frozenset[str] | None = None,
) -> dict[str, ObjectState]:
    """Fetch states for all map objects using batch queries where supported.

    Objects are binned by kind (:func:`_bin_map_elements`) and each kind is
    resolved by a dedicated helper that writes into the shared ``results`` map.
    The helpers run in sequence because the host helper's output feeds the
    service-summary/recognize-services enrichment.

    ``map_cfg_cache`` memoises ``map_service.get_map`` across the full
    map-link recursion so a map referenced by several sibling or nested maps
    loads only once. The cache stores ``None`` for not-found maps to avoid
    retrying missing names.

    ``_visited_maps`` carries the set of map names already on the current
    recursion path so map-link aggregation can transitively include nested
    maps without infinite-looping on cycles.
    """
    if map_cfg_cache is None:
        map_cfg_cache = {}
    if _visited_maps is None:
        _visited_maps = frozenset()

    bins = _bin_map_elements(objects)
    results: dict[str, ObjectState] = {}

    await _resolve_host_states(connection, bins.hosts_soft, bins.hosts_hard, auth_user, results)
    await _resolve_service_states(connection, bins.svcs_soft, bins.svcs_hard, auth_user, results)
    await _resolve_individual_states(connection, bins.lines + bins.others, results)
    await _resolve_map_link_states(
        bins.map_objects,
        auth_user=auth_user,
        map_cfg_cache=map_cfg_cache,
        visited_maps=_visited_maps,
        results=results,
    )

    return results


def _aggregate_host_with_services_from_data(
    host_state: ObjectState, services: list[ServiceRow]
) -> ObjectState:
    """Aggregate a pre-fetched host state with its services (no I/O)."""
    if not services:
        return host_state
    all_states = [host_state.state] + [s.get("state", "PENDING") for s in services]
    worst = max(all_states, key=lambda s: SEVERITY_RANK.get(s, 0))
    if worst == host_state.state:
        return host_state
    return ObjectState(
        object_id=host_state.object_id,
        type="host",
        state=worst,
        output=host_state.output,
        perf_data=host_state.perf_data,
        acknowledged=host_state.acknowledged,
        in_downtime=host_state.in_downtime,
    )


async def _get_object_state(connection: ConnectionBase, obj: MapElement) -> ObjectState:
    try:
        if obj.type == "host" and obj.host_name:
            if obj.only_hard_states:
                state = await connection.get_host_hard_state(obj.host_name)
            else:
                state = await connection.get_host_state(obj.host_name)
            if obj.recognize_services:
                state = await _aggregate_host_with_services(connection, state, obj.host_name)
        elif obj.type == "service" and obj.host_name and obj.service_description:
            if obj.only_hard_states:
                state = await connection.get_service_hard_state(
                    obj.host_name, obj.service_description
                )
            else:
                state = await connection.get_service_state(obj.host_name, obj.service_description)
        elif obj.type == "hostgroup" and obj.group_name:
            state = await connection.get_hostgroup_states(obj.group_name)
        elif obj.type == "servicegroup" and obj.group_name:
            state = await connection.get_servicegroup_states(obj.group_name)
        elif obj.type == "dyngroup" and obj.object_filter:
            state = await connection.get_dyngroup_state(
                obj.object_types or "host", obj.object_filter
            )
            if obj.bundle_kind is not None and (obj.object_types or "host") == "host":
                state.state = _combined_state_from_summary(state.state, state.services_summary)
        elif obj.type == "line" and obj.host_name and obj.service_description:
            state = await connection.get_service_state(obj.host_name, obj.service_description)
        elif obj.type == "line" and obj.host_name:
            state = await connection.get_host_state(obj.host_name)
        elif obj.type == "graph" and obj.host_name and obj.service_description:
            state = await connection.get_service_state(obj.host_name, obj.service_description)
        elif obj.type == "graph" and obj.host_name:
            state = await connection.get_host_state(obj.host_name)
        else:
            state = ObjectState(object_id=obj.id, type=obj.type, state="PENDING")
        state.object_id = obj.id
        return state
    except Exception as exc:
        logger.exception(
            "Error fetching state for object %(object_id)s: %(error)s",
            {"object_id": obj.id, "error": exc},
        )
        return ObjectState(object_id=obj.id, type=obj.type, state="PENDING", stale=True)


async def _aggregate_host_with_services(
    connection: ConnectionBase, host_state: ObjectState, hostname: str
) -> ObjectState:
    """Aggregate host state with the worst state of all its services."""
    try:
        services = await connection.get_host_services(hostname)
    except Exception:
        return host_state
    return _aggregate_host_with_services_from_data(host_state, services)


async def _resolve_primary_host(connection: ConnectionBase) -> str | None:
    """Pick the connection's primary host for auto-host bindings.

    Prefers the Checkmk server's own host (named like the site, else
    ``localhost``) so shipped maps land on the server that always exists on a
    fresh install; falls back to the first host alphabetically. Returns ``None``
    on an empty site (the tiles then stay unbound placeholders).
    """
    try:
        hosts = await connection.get_all_hosts_states()
    except Exception:
        logger.warning("primary-host resolution failed", exc_info=True)
        return None
    if not hosts:
        return None
    for preferred in (settings.checkmk_site, "localhost"):
        if preferred and preferred in hosts:
            return preferred
    return sorted(hosts)[0]


async def _get_presentation_states(
    cfg: MapConfig,
    connection: ConnectionBase,
    auth_user: str | None = None,
) -> MapStates:
    """Resolve live states for the bound data elements of a presentation map.

    Bound elements are adapted to transient ``MapElement``s and run through the
    shared ``_states_for_objects`` pipeline so per-connection batching, auth
    scoping and ``ObjectState`` shaping are reused. Results key by element id, so
    the frontend states store lights up the matching element with no extra wiring.
    """
    pv = cfg.view if isinstance(cfg.view, PresentationView) else PresentationView()
    bindable = [el for el in pv.elements if isinstance(el, DataElement | ShapeElement)]

    # Auto-host tiles (shipped/template maps) bind to the connection's primary
    # host, resolved once here, so they light up on a fresh install without a
    # hard-coded host name. An explicit host/group/aggregation always wins.
    needs_primary = any(
        el.auto_host and not (el.host_name or el.group_name or el.aggregation_id) for el in bindable
    )
    primary_host = await _resolve_primary_host(connection) if needs_primary else None

    def _host_of(el: DataElement | ShapeElement) -> str | None:
        if el.host_name:
            return el.host_name
        if el.auto_host and not (el.group_name or el.aggregation_id):
            return primary_host
        return None

    bound = [el for el in bindable if _host_of(el) or el.group_name or el.aggregation_id]

    def _object_type(el: DataElement | ShapeElement) -> ObjectType:
        # Explicit object_type wins; legacy elements without one keep the
        # original host/service derivation. Mirrors the frontend's ``bindKind``
        # (PresentationBindingForm.vue) — change both together.
        if el.object_type:
            return el.object_type
        if el.aggregation_id:
            return "aggregation"
        return "service" if el.service_description else "host"

    objects = [
        MapElement(
            id=el.id,
            type=_object_type(el),
            connection_id=el.connection_id,
            host_name=_host_of(el),
            service_description=el.service_description,
            group_name=el.group_name,
            aggregation_id=el.aggregation_id,
            only_hard_states=el.only_hard_states,
        )
        for el in bound
    ]

    state_map = await _states_for_objects(
        objects,
        default_connection=connection,
        default_connection_id=cfg.connection_id,
        auth_user=auth_user,
        visited_maps=frozenset({cfg.name}),
    )
    states = list(state_map.values())

    connection_ok = await _derive_connection_ok(states, connection)

    return MapStates(
        map_name=cfg.name,
        states=states,
        generated_at=time.time(),
        connection_ok=connection_ok,
        runtime=get_daemon_runtime(),
    )


async def _get_radar_states(cfg: MapConfig, connection: ConnectionBase) -> MapStates:
    """Fetch states for all dynamically resolved radar map members."""
    rv = cfg.view if isinstance(cfg.view, RadarView) else RadarView()
    states: list[ObjectState] = []

    if rv.filter == "all_hosts":
        try:
            host_batch = await connection.get_all_hosts_states()
        except Exception:
            host_batch = {}
        # Operators expect to see the service-state breakdown when clicking a host
        # in the radar drawer — without this the chip row stays empty for radar
        # maps even though the data is one cheap query away.
        if host_batch:
            try:
                summaries = await connection.get_services_summary(list(host_batch.keys()))
            except Exception:
                summaries = {}
        else:
            summaries = {}
        for host, s in host_batch.items():
            s.object_id = host
            if s.services_summary is None and host in summaries:
                s.services_summary = summaries[host]
            states.append(s)
    elif rv.filter == "all_services":
        try:
            svc_batch_all = await connection.get_all_services_states()
        except Exception:
            svc_batch_all = {}
        for (host, svc), s in svc_batch_all.items():
            member_id = f"{host};{svc}"
            s.object_id = member_id
            states.append(s)
    else:
        members = await connection.get_group_members(rv.filter, rv.filter_value)
        if not members:
            return MapStates(
                map_name=cfg.name,
                states=[],
                generated_at=time.time(),
                connection_ok=True,
                runtime=get_daemon_runtime(),
            )
        host_members = [m for m in members if ";" not in m]
        svc_members: list[tuple[str, str, str]] = []
        for m in members:
            if ";" in m:
                host, svc = m.split(";", 1)
                svc_members.append((m, host, svc))

        if host_members:
            try:
                batch = await connection.get_hosts_states(host_members)
            except Exception:
                batch = {}
            try:
                summaries = await connection.get_services_summary(host_members)
            except Exception:
                summaries = {}
            for h in host_members:
                s = batch.get(h) or ObjectState(
                    object_id=h, type="host", state="PENDING", stale=True
                )
                s.object_id = h
                if s.services_summary is None and h in summaries:
                    s.services_summary = summaries[h]
                states.append(s)

        if svc_members:
            pairs = [(host, svc) for (_, host, svc) in svc_members]
            try:
                svc_batch = await connection.get_services_states(pairs)
            except Exception:
                svc_batch = {}
            for member_id, host, svc in svc_members:
                s = svc_batch.get((host, svc)) or ObjectState(
                    object_id=member_id, type="service", state="PENDING", stale=True
                )
                s.object_id = member_id
                states.append(s)

    connection_ok = bool(states) and not all(s.stale for s in states)
    return MapStates(
        map_name=cfg.name,
        states=states,
        generated_at=time.time(),
        connection_ok=connection_ok,
        runtime=get_daemon_runtime(),
    )


@contextmanager
def _gc_paused() -> Iterator[None]:
    """Pause cyclic GC for an allocation-heavy synchronous block.

    Building (or sig-walking) a 100k+-node folder tree allocates in one burst,
    which repeatedly triggers full GC passes over the ever-growing, garbage-free
    object graph and roughly doubles the wall time. The wrapped block never
    awaits, so the pause is invisible to the rest of the event loop.
    """
    if not gc.isenabled():
        yield
        return
    gc.disable()
    try:
        yield
    finally:
        gc.enable()


def _norm_folder_path(path: str) -> str:
    return path.strip("/")


def _prettify_folder_title(slug: str) -> str:
    """Slug → readable title: '_'/'-' → space, Title-Case."""
    pretty = " ".join(w.capitalize() for w in slug.replace("-", " ").replace("_", " ").split())
    return pretty or "Main"


def _combined_state_from_summary(host_state: str, summary: ServicesSummary | None) -> str:
    """Worst of the host state and its service-summary counts."""
    if summary is None:
        return host_state
    # Branch ladder instead of max()-over-candidates: this runs once per host
    # per tick (100k+ on large sites), where the list + lambda dominated.
    rank = SEVERITY_RANK.get(host_state, 0)
    if summary.critical and rank < SEVERITY_RANK["CRITICAL"]:
        return "CRITICAL"
    if summary.warning and rank < SEVERITY_RANK["WARNING"]:
        return "WARNING"
    if summary.unknown and rank < SEVERITY_RANK["UNKNOWN"]:
        return "UNKNOWN"
    return host_state


async def _get_folder_tree_states(cfg: MapConfig, connection: ConnectionBase) -> MapStates:
    """Resolve + aggregate a SETUP folder-tree map.

    Folders bubble the worst state of everything below them; a (recursively)
    hostless folder gets the synthetic ``EMPTY`` state, which is excluded from a
    parent's worst-state roll-up. ``problems_only`` / ``show_empty_folders``
    prune the tree; ``root_folder`` scopes it to a subtree.
    """
    fv = cfg.view if isinstance(cfg.view, FolderTreeView) else FolderTreeView()
    fetch_ok = True
    try:
        data = await connection.get_folder_tree(
            only_hard=fv.only_hard_states, sites=fv.sites or None
        )
    except Exception:
        logger.exception("Folder-tree fetch failed for map %(map)s", {"map": cfg.name})
        data = FolderTreeData()
        fetch_ok = False

    with _gc_paused():
        root = _build_folder_tree(data, fv)

    return MapStates(
        map_name=cfg.name,
        states=[],
        generated_at=time.time(),
        connection_ok=fetch_ok,
        dead_sites=data.dead_sites,
        folder_tree=root,
        runtime=get_daemon_runtime(),
    )


def _build_folder_tree(data: FolderTreeData, fv: FolderTreeView) -> FolderTreeNode:
    """Assemble + aggregate the folder tree from raw connection data.

    Hot path: runs per SSE tick per subscriber group over every host of the
    connection, so the host loop and ``finalize`` are written allocation- and
    attribute-access-lean (locals bound, one pass per node).
    """
    nodes: dict[str, FolderTreeNode] = {}

    def ensure_folder(
        path: str,
        title: str | None = None,
        folder_id: str = "",
        permitted: bool | None = None,
    ) -> FolderTreeNode:
        # ``permitted`` is None for implicit (ancestor) and host-folder creation,
        # which default to permitted; only the explicit skeleton pass carries the
        # real Checkmk folder permission and may downgrade an existing node.
        path = _norm_folder_path(path)
        node = nodes.get(path)
        if node is None:
            leaf_slug = path.rsplit("/", 1)[-1] if path else ""
            node = FolderTreeNode(
                path=path,
                title=title or _prettify_folder_title(leaf_slug),
                kind="folder",
                state="EMPTY",
                is_empty=True,
                folder_id=folder_id,
                permitted=permitted if permitted is not None else True,
            )
            nodes[path] = node
            if path:
                parent = path.rsplit("/", 1)[0] if "/" in path else ""
                ensure_folder(parent).children.append(node)
        else:
            if title and node.title == _prettify_folder_title(
                path.rsplit("/", 1)[-1] if path else ""
            ):
                node.title = title
            if folder_id and not node.folder_id:
                node.folder_id = folder_id
            if permitted is not None:
                node.permitted = permitted
        return node

    ensure_folder("")
    for f in data.folders:
        ensure_folder(f["path"], f.get("title"), f.get("folder_id", ""), f.get("permitted", True))

    # Hosts live only as tree nodes; the flat ``states`` list is left empty (see
    # the MapStates return). At 100k+ hosts duplicating every host into ``states``
    # doubled the payload for data the tree node already carries.
    # ``folder_cache`` collapses the per-host normalise + ensure_folder lookup —
    # hosts cluster heavily into few folders. Leaf problem/severity counts are
    # set at construction so ``finalize`` never has to revisit the 100k+ leaves.
    sev_get = SEVERITY_RANK.get
    folder_cache: dict[str, tuple[str, list[FolderTreeNode]]] = {}
    for h in data.hosts:
        cached = folder_cache.get(h["folder_path"])
        if cached is None:
            fpath = _norm_folder_path(h["folder_path"])
            cached = folder_cache[h["folder_path"]] = (fpath, ensure_folder(fpath).children)
        fpath, siblings = cached
        host_name = h["host_name"]
        summary = h.get("services_summary")
        combined = _combined_state_from_summary(h["state"], summary)
        is_problem = sev_get(combined, 0) > 0
        siblings.append(
            FolderTreeNode(
                path=f"{fpath}/{host_name}" if fpath else host_name,
                title=host_name,
                kind="host",
                state=combined,
                host_count=1,
                problem_count=1 if is_problem else 0,
                # Only hosts feed the severity breakdown; service leaves never do.
                severity_counts={combined: 1} if is_problem else {},
                output=h.get("output", ""),
                acknowledged=h.get("acknowledged", False),
                in_downtime=h.get("in_downtime", False),
                is_flapping=h.get("is_flapping", False),
                stale=h.get("stale", False),
                last_state_change=h.get("last_state_change"),
                site_id=h.get("site_id"),
                services_summary=summary,
            )
        )

    # Service leaves are NOT materialised here. ``show_services`` instead makes
    # hosts expandable on demand: the frontend fetches a single host's services
    # via the folder-host-services endpoint only when the operator drills into
    # that host. Eagerly querying every service (get_all_services_states ignores
    # the folder scope) would push tens of millions of rows on large sites — the
    # map must scale to 4M-host environments.
    def finalize(node: FolderTreeNode) -> None:
        # Leaves carry their counts from construction; folders aggregate all
        # children in a single pass (count sums, severity merge, worst-state).
        host_count = 0
        problem_count = 0
        counts: dict[str, int] = {}
        worst: str | None = None
        worst_rank = 0
        for child in node.children:
            if child.kind == "folder":
                finalize(child)
                if child.is_empty:
                    # Recursively hostless: nothing to add, and the synthetic
                    # EMPTY state must not feed the parent's worst-state.
                    continue
            host_count += child.host_count
            problem_count += child.problem_count
            if child.severity_counts:
                for st, n in child.severity_counts.items():
                    counts[st] = counts.get(st, 0) + n
            rank = sev_get(child.state, 0)
            if worst is None or rank > worst_rank:
                worst, worst_rank = child.state, rank
        node.host_count = host_count
        node.problem_count = problem_count
        node.severity_counts = counts
        if worst is not None:
            node.is_empty = False
            node.state = worst
        else:
            node.is_empty = True
            node.state = "EMPTY"
        # Display order: a folder's own hosts first, then its subfolders — so it
        # is obvious which hosts belong directly to this folder (e.g. Main's
        # hosts sit right under Main, before the subfolders). Within each group
        # worst-severity first (problems float up), then alphabetical;
        # EMPTY/PENDING sink below healthy via the -1 default.
        node.children.sort(
            key=lambda c: (
                c.kind == "folder",
                -sev_get(c.state, -1),
                c.title.lower(),
            )
        )

    # Resolve the display root (stable folder_id first, then path).
    root_path = ""
    if fv.root_folder:
        by_id = next(
            (p for p, n in nodes.items() if n.folder_id and n.folder_id == fv.root_folder), None
        )
        cand = _norm_folder_path(fv.root_folder)
        root_path = by_id if by_id is not None else (cand if cand in nodes else "")
    root = nodes.get(root_path) or nodes[""]
    finalize(root)

    # problems_severity narrows what problems_only keeps: "critical" only
    # retains CRITICAL/DOWN/UNREACHABLE — on typical sites nearly every host
    # carries some WARNING service, making the "any" filter almost a no-op.
    critical_only = fv.problems_severity == "critical"

    def _node_is_problem(node: FolderTreeNode) -> bool:
        if node.kind == "folder":
            if critical_only:
                return any(node.severity_counts.get(s, 0) > 0 for s in CRITICAL_STATES)
            return node.problem_count > 0
        if critical_only:
            return node.state in CRITICAL_STATES
        return node.problem_count > 0

    def prune(node: FolderTreeNode) -> bool:
        """Return True to keep; applies problems_only + show_empty_folders."""
        if node.kind != "folder":
            return (not fv.problems_only) or _node_is_problem(node)
        node.children = [c for c in node.children if prune(c)]
        if fv.problems_only:
            return _node_is_problem(node)
        # An empty folder the user has no Checkmk read-permission to is never
        # shown — otherwise the SETUP folder name would leak to a user outside
        # its contact groups (even though all its hosts are already hidden).
        # Folders that contain a visible host are not empty, so they survive.
        if node.is_empty and not node.permitted:
            return False
        return fv.show_empty_folders or not node.is_empty

    prune(root)
    return root


# ---------------------------------------------------------------------------
# Flow Map topology snapshots — used by the broadcast loop to
# emit incremental updates instead of re-sending the full topology every tick.
# ---------------------------------------------------------------------------


def drop_map_snapshots[V](snapshot: dict[tuple[str, str | None], V], map_name: str) -> None:
    """Drop every (map, user) entry for ``map_name`` from a snapshot dict.

    The broadcast-loop snapshot dicts are keyed by ``(map_name, auth_user)``;
    forgetting a map means removing all of its per-user entries.
    """
    for key in [k for k in snapshot if k[0] == map_name]:
        snapshot.pop(key, None)


def prune_map_snapshots[V](
    snapshot: dict[tuple[str, str | None], V],
    map_name: str,
    live_groups: Collection[str | None],
) -> None:
    """Drop ``map_name`` entries whose group key is no longer subscribed.

    Subscribers come and go while a map's broadcast loop runs; without this the
    per-group snapshot dicts accumulate dead ``(map, group)`` entries until the
    loop finally exits. Called each tick with the currently-subscribed groups.
    """
    for key in [k for k in snapshot if k[0] == map_name and k[1] not in live_groups]:
        snapshot.pop(key, None)


# (map_name, auth_user) → (host_name → volatile-fields hash)
_topology_snapshots: dict[tuple[str, str | None], dict[str, int]] = {}
# Parallel to _topology_snapshots, hashing only the check-timing fields that
# _hash_topology_node deliberately omits. Lets compute_topology_delta emit a
# slim timing patch for hosts that re-checked but didn't otherwise change.
_topology_timing_snapshots: dict[tuple[str, str | None], dict[str, int]] = {}


def _hash_topology_node_timing(n: TopologyNode) -> int:
    """Hash the check-timing fields excluded from _hash_topology_node.

    Host last/next check + current_attempt, plus each service's last/next check
    (bounded — the topology truncates services to the top-N), so a recheck on the
    host or any of its listed services produces a timing patch.
    """
    services = tuple((sv.name, sv.last_check, sv.next_check) for sv in n.services)
    return hash((n.last_check, n.next_check, n.current_attempt, services))


def _hash_topology_node(n: TopologyNode) -> int:
    """Hash only operationally-significant fields.

    Stable identity/topology fields (name, parents, alias, address) are
    excluded — they're carried in `added` payloads and don't trigger
    `changed` entries on their own.

    Excluded for delta purposes (still travel inside any node that *does*
    get re-sent, just don't trigger a re-send on their own):
    - ``last_check``/``next_check``/``current_attempt`` — tick every
      Checkmk re-check (often ~30 s) regardless of whether anything real
      changed. Including them makes every host flap as ``changed`` and
      defeats the delta.
    - ``output`` (host *and* per-service) — typically embeds live latency
      like ``"OK - 127.0.0.1 rta 0.022ms lost 0%"`` which churns every
      check. Output text is rarely the *operationally* interesting bit;
      state transitions are.
    """
    s = n.services_summary
    summary = (s.ok, s.warning, s.critical, s.unknown, s.pending) if s is not None else ()
    services = tuple((sv.name, sv.state) for sv in n.services)
    return hash(
        (
            n.state,
            n.last_state_change,
            n.acknowledged,
            n.in_downtime,
            n.notifications_enabled,
            n.active_checks_enabled,
            n.services_omitted,
            n.services_truncated_count,
            summary,
            services,
        )
    )


def compute_topology_delta(
    map_name: str,
    auth_user: str | None,
    current: list[TopologyNode],
    *,
    force_full: bool = False,
    store: bool = True,
) -> TopologyDelta:
    """Diff `current` against the previous snapshot for (map_name, auth_user).

    Side effect (unless ``store=False``): stores the new snapshot in
    `_topology_snapshots` so the next call returns deltas relative to this one.
    Pass ``store=False`` to build a one-off full for a single joining subscriber
    without disturbing the shared snapshot the rest of the group diffs against.

    ``timing`` carries check-timing-only patches for hosts that re-checked but
    aren't in ``added``/``changed`` (those already ship fresh timing), so the
    Flow Map's next-check / overdue readouts stay live without re-sending whole
    nodes. Empty on a full send (timing rides inside the node payloads).
    """
    key = (map_name, auth_user)
    prev = _topology_snapshots.get(key)
    prev_timing = _topology_timing_snapshots.get(key)
    new_hashes = {n.name: _hash_topology_node(n) for n in current}
    new_timing = {n.name: _hash_topology_node_timing(n) for n in current}

    if force_full or prev is None:
        if store:
            _topology_snapshots[key] = new_hashes
            _topology_timing_snapshots[key] = new_timing
        return TopologyDelta(full=True, generated_at=time.time(), added=current)

    by_name = {n.name: n for n in current}
    added = [n for n in current if n.name not in prev]
    changed = [n for n in current if n.name in prev and new_hashes[n.name] != prev[n.name]]
    removed = [name for name in prev if name not in by_name]

    resent = {n.name for n in added} | {n.name for n in changed}
    timing = [
        TopologyTiming(
            name=n.name,
            last_check=n.last_check,
            next_check=n.next_check,
            current_attempt=n.current_attempt,
            services=[
                ServiceTiming(name=sv.name, last_check=sv.last_check, next_check=sv.next_check)
                for sv in n.services
            ],
        )
        for n in current
        if n.name not in resent
        and (prev_timing is None or new_timing[n.name] != prev_timing.get(n.name))
    ]

    if store:
        _topology_snapshots[key] = new_hashes
        _topology_timing_snapshots[key] = new_timing
    return TopologyDelta(
        full=False,
        generated_at=time.time(),
        added=added,
        changed=changed,
        removed=removed,
        timing=timing,
    )


def drop_topology_snapshot(map_name: str, auth_user: str | None = None) -> None:
    """Forget the snapshot for a map (call when broadcast loop ends or map is deleted).

    With `auth_user=None`, drops snapshots for *all* users of the map.
    """
    if auth_user is not None:
        _topology_snapshots.pop((map_name, auth_user), None)
        _topology_timing_snapshots.pop((map_name, auth_user), None)
        return
    drop_map_snapshots(_topology_snapshots, map_name)
    drop_map_snapshots(_topology_timing_snapshots, map_name)


# ---------------------------------------------------------------------------
# Object-state delta encoding for the broadcast loop. Without this,
# every tick re-sends the full state map (~600 B per object × N objects × M
# clients × every state_refresh_interval). Most checks are unchanged tick to
# tick, so the delta is much smaller in steady state.
# ---------------------------------------------------------------------------

# (map_name, auth_user) → (object_id → volatile-fields hash)
_state_snapshots: dict[tuple[str, str | None], dict[str, int]] = {}
# Separate from _state_snapshots so timing-only ticks ride a slim ObjectTiming
# patch instead of forcing a full-state re-send.
_timing_snapshots: dict[tuple[str, str | None], dict[str, int]] = {}


def _hash_object_timing(s: ObjectState) -> int:
    return hash((s.last_check, s.next_check, s.current_attempt))


def _hash_object_state(s: ObjectState) -> int:
    """Hash only operationally-significant fields.

    Excluded from the change-detection hash (they still ride along inside any
    state that *does* get re-sent, just don't trigger a re-send on their own):
    - ``last_check``/``next_check``/``current_attempt`` — tick every Checkmk
      re-check regardless of whether anything real changed.
    - ``output`` — typically embeds live latency like ``"OK - rta 0.022ms"``
      that fluctuates every check; the operationally interesting bit is the
      state transition, not the text.

    ``perf_data`` *is* included because the frontend appends it to per-object
    metric history on every push — dropping it would freeze the live graphs.
    """
    summary = s.services_summary
    summary_t = (
        (summary.ok, summary.warning, summary.critical, summary.unknown, summary.pending)
        if summary is not None
        else ()
    )
    # AggregationNode is recursive and not directly tuple-hashable. Pydantic
    # JSON dump is fast (Rust core) and only runs for aggregation objects.
    tree_repr = s.tree.model_dump_json() if s.tree is not None else ""
    return hash(
        (
            s.state,
            s.perf_data,
            s.check_command,
            s.acknowledged,
            s.in_downtime,
            s.stale,
            s.notifications_enabled,
            s.active_checks_enabled,
            s.state_type,
            s.max_attempts,
            s.last_state_change,
            s.site_id,
            summary_t,
            tree_repr,
        )
    )


def compute_states_delta(
    map_name: str,
    auth_user: str | None,
    current: list[ObjectState],
    *,
    force_full: bool = False,
) -> tuple[list[ObjectState], list[str], bool, list[ObjectTiming]]:
    """Diff `current` against the previous snapshot for (map, auth_user).

    Returns ``(states_to_send, removed_ids, full, timing)``:
    - ``states_to_send``: full list when ``full=True``; else only added or changed entries
    - ``removed_ids``: object_ids no longer present (only meaningful when ``full=False``)
    - ``full``: ``True`` on first call (no prior snapshot) or when ``force_full=True``
    - ``timing``: slim check-timing patches for objects whose timing changed but
      that aren't in ``states_to_send`` (those already carry fresh timing). Empty
      on a full send, which carries timing inside the state objects.

    Side effect: stores the new state and timing hashes so the next call diffs
    against this.
    """
    key = (map_name, auth_user)
    prev = _state_snapshots.get(key)
    prev_timing = _timing_snapshots.get(key)
    new_hashes = {s.object_id: _hash_object_state(s) for s in current}
    new_timing = {s.object_id: _hash_object_timing(s) for s in current}

    if force_full or prev is None:
        _state_snapshots[key] = new_hashes
        _timing_snapshots[key] = new_timing
        return current, [], True, []

    by_id = {s.object_id: s for s in current}
    to_send = [
        s
        for s in current
        if s.object_id not in prev or new_hashes[s.object_id] != prev[s.object_id]
    ]
    to_send_ids = {s.object_id for s in to_send}
    removed = [oid for oid in prev if oid not in by_id]
    timing = [
        ObjectTiming(
            object_id=s.object_id,
            last_check=s.last_check,
            next_check=s.next_check,
            current_attempt=s.current_attempt,
        )
        for s in current
        if s.object_id not in to_send_ids
        and (prev_timing is None or new_timing[s.object_id] != prev_timing.get(s.object_id))
    ]
    _state_snapshots[key] = new_hashes
    _timing_snapshots[key] = new_timing
    return to_send, removed, False, timing


# path -> (field_sig, child_paths) per (map, auth_user); the diff source for
# folder-tree deltas (only changed nodes travel, not the whole tree each tick).
_folder_tree_snapshots: dict[tuple[str, str | None], dict[str, tuple[int, tuple[str, ...]]]] = {}


def _ft_field_sig(node: FolderTreeNode) -> int:
    # Live fields that, when changed, must reach the client — EXCEPT ``output``
    # (plugin text drifts every re-check; sent along when a node patches anyway).
    ss = node.services_summary
    return hash(
        (
            node.title,  # a WATO folder rename keeps the path but changes the title
            node.site_id,
            node.state,
            node.is_empty,
            node.host_count,
            node.problem_count,
            tuple(sorted(node.severity_counts.items())),
            node.acknowledged,
            node.in_downtime,
            node.is_flapping,
            node.stale,
            node.last_state_change,
            None if ss is None else (ss.ok, ss.warning, ss.critical, ss.unknown, ss.pending),
        )
    )


def _ft_patch(node: FolderTreeNode, include_order: bool) -> FolderTreeNodePatch:
    return FolderTreeNodePatch(
        path=node.path,
        title=node.title,
        site_id=node.site_id,
        state=node.state,
        is_empty=node.is_empty,
        host_count=node.host_count,
        problem_count=node.problem_count,
        severity_counts=node.severity_counts,
        output=node.output,
        acknowledged=node.acknowledged,
        in_downtime=node.in_downtime,
        is_flapping=node.is_flapping,
        stale=node.stale,
        last_state_change=node.last_state_change,
        services_summary=node.services_summary,
        children_order=[c.path for c in node.children] if include_order else None,
    )


def compute_folder_tree_delta(
    map_name: str, auth_user: str | None, tree: FolderTreeNode | None
) -> FolderTreeDelta:
    """Diff a folder tree against the last snapshot for (map, auth_user).

    Returns ``full`` (whole tree) on the first tick or any structural change
    (a node added/removed/moved — all change the set of paths); otherwise only
    the nodes whose live fields or child order changed. The host-state delta in
    :func:`compute_states_delta` is blind to the bubbled folder structure, so the
    tree carries its own delta. Side effect: stores the new snapshot.
    """
    key = (map_name, auth_user)
    prev = _folder_tree_snapshots.get(key)
    if tree is None:
        _folder_tree_snapshots.pop(key, None)
        return FolderTreeDelta(full=True, tree=None)

    flat: dict[str, tuple[int, tuple[str, ...]]] = {}
    by_path: dict[str, FolderTreeNode] = {}
    with _gc_paused():
        field_sig = _ft_field_sig
        stack = [tree]
        while stack:
            n = stack.pop()
            children = n.children
            flat[n.path] = (
                field_sig(n),
                tuple([c.path for c in children]) if children else (),
            )
            by_path[n.path] = n
            if children:
                stack.extend(children)

        # Path set changing = a node added/removed/moved (paths are hierarchical,
        # so a move changes the moved node's path too) → can't express as field
        # patches.
        full = prev is None or prev.keys() != flat.keys()
        _folder_tree_snapshots[key] = flat
        if full:
            return FolderTreeDelta(full=True, tree=tree)
        assert prev is not None  # full would be True otherwise

        changed: list[FolderTreeNodePatch] = []
        for path, (fsig, child_paths) in flat.items():
            old_fsig, old_children = prev[path]
            order_changed = old_children != child_paths
            if old_fsig != fsig or order_changed:
                changed.append(_ft_patch(by_path[path], order_changed))
        return FolderTreeDelta(full=False, changed=changed)


def drop_states_snapshot(map_name: str, auth_user: str | None = None) -> None:
    """Forget the snapshot for a map (call when broadcast loop ends or map is deleted).

    With ``auth_user=None``, drops snapshots for *all* users of the map.
    """
    if auth_user is not None:
        _state_snapshots.pop((map_name, auth_user), None)
        _timing_snapshots.pop((map_name, auth_user), None)
        _folder_tree_snapshots.pop((map_name, auth_user), None)
        return
    drop_map_snapshots(_state_snapshots, map_name)
    drop_map_snapshots(_timing_snapshots, map_name)
    drop_map_snapshots(_folder_tree_snapshots, map_name)


def prune_group_snapshots(map_name: str, live_groups: Collection[str | None]) -> None:
    """Drop every per-group delta snapshot for a map whose group left the stream.

    Covers all the broadcast-loop snapshot stores owned by this module (object
    state, timing, folder tree, topology). Called each tick so a long-lived map
    doesn't retain snapshots for groups whose subscribers have all disconnected.
    """
    prune_map_snapshots(_state_snapshots, map_name, live_groups)
    prune_map_snapshots(_timing_snapshots, map_name, live_groups)
    prune_map_snapshots(_folder_tree_snapshots, map_name, live_groups)
    prune_map_snapshots(_topology_snapshots, map_name, live_groups)
    prune_map_snapshots(_topology_timing_snapshots, map_name, live_groups)
