#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Monitoring state schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from cmk.maps.backend.schemas.map import AggregationNode
from cmk.maps.backend.schemas.settings import DaemonRuntime

HostStateValue = Literal["UP", "DOWN", "UNREACHABLE", "PENDING"]
ServiceStateValue = Literal["OK", "WARNING", "CRITICAL", "UNKNOWN", "PENDING"]
# Synthetic states that may also appear on ObjectState.state:
#   NO_PERMISSION — caller lacks contact-group access for this object
#   NOT_FOUND     — host/service/group is absent from monitoring data entirely


class ServicesSummary(BaseModel):
    ok: int = 0
    warning: int = 0
    critical: int = 0
    unknown: int = 0
    pending: int = 0


class ObjectState(BaseModel):
    object_id: str
    type: str
    state: str
    output: str = ""
    perf_data: str = ""
    # Together with perf_data this is the input the GUI's metric-info endpoint
    # (the maps_metric_info endpoint) needs — the client resolves display semantics
    # (Perf-O-Meter, units, titles) there instead of asking this daemon.
    check_command: str = ""
    acknowledged: bool = False
    in_downtime: bool = False
    stale: bool = False
    notifications_enabled: bool = True
    active_checks_enabled: bool = True
    address: str = ""
    alias: str = ""
    last_check: float | None = None
    next_check: float | None = None
    state_type: str = ""  # "HARD" | "SOFT" | ""
    current_attempt: int = 0
    max_attempts: int = 0
    last_state_change: float | None = None
    # Set in distributed Checkmk setups to identify the originating site.
    site_id: str | None = None
    # Populated only for type=='aggregation' when the MapElement has expand_depth > 0.
    tree: AggregationNode | None = None
    # Aggregated service-state counts; populated only for type=='host'.
    services_summary: ServicesSummary | None = None
    # Member host-state counts (UP→ok, DOWN→critical, UNREACHABLE→unknown);
    # populated for host dyngroups so the UI can show a "Hosts" pill row.
    hosts_summary: ServicesSummary | None = None


class ObjectTiming(BaseModel):
    """Slim check-timing patch for the fields excluded from the state-delta
    hash. Without it they freeze on the client and "check overdue" grows with
    the map's open time."""

    object_id: str
    last_check: float | None = None
    next_check: float | None = None
    current_attempt: int = 0


class CommentInfo(BaseModel):
    id: int
    author: str
    comment: str
    entry_time: float
    expire_time: float | None = None


class DowntimeInfo(BaseModel):
    id: int
    author: str
    comment: str
    start_time: float
    end_time: float
    fixed: bool = True


class ObjectDetails(BaseModel):
    """Extended object info loaded on demand (Drawer, Properties modal).

    Kept separate from ``ObjectState`` so the stream stays compact —
    long_output, comments, downtimes and topology can each be many KB and
    rarely change between checks.
    """

    type: Literal["host", "service"]
    host_name: str
    service_description: str | None = None
    long_output: str = ""
    check_command: str = ""
    latency: float | None = None
    execution_time: float | None = None
    is_flapping: bool = False
    in_notification_period: bool = True
    last_time_ok: float | None = None  # service only
    notification_period: str = ""
    check_interval: float | None = None
    parents: list[str] = []
    children: list[str] = []
    host_groups: list[str] = []
    service_groups: list[str] = []
    contact_groups: list[str] = []
    labels: dict[str, str] = {}
    comments: list[CommentInfo] = []
    downtimes: list[DowntimeInfo] = []


class FolderTreeNode(BaseModel):
    """A node in a SETUP folder-tree map.

    ``kind`` distinguishes folders from host/service leaves. Folders carry an
    aggregated worst-state across everything below them, or the synthetic
    ``"EMPTY"`` state when (recursively) hostless — ``EMPTY`` is ranked outside
    the normal severity scale and excluded from the parent's worst-state.
    """

    path: str  # folder path key, e.g. "datacenters/muc" ("" = root)
    title: str  # display title (real, or prettified slug)
    kind: Literal["folder", "host", "service"] = "folder"
    state: str  # aggregated/own state; "EMPTY" for hostless folders
    is_empty: bool = False
    # Whether the requesting user may see this folder (Checkmk folder permissions:
    # see-all, or member of the folder's contact groups). Empty + non-permitted
    # folders are pruned so a scoped user never sees SETUP folder names they have
    # no access to. Internal-only — drives pruning, not sent to the client.
    permitted: bool = Field(default=True, exclude=True)
    folder_id: str = ""  # stable WATO ``__id`` when known
    host_count: int = 0  # hosts at/below this node
    problem_count: int = 0  # non-OK hosts at/below (for badges)
    # Hosts at/below this node grouped by their combined state, problem states
    # only (e.g. {"CRITICAL": 4, "WARNING": 46}). Powers severity-aware badges.
    severity_counts: dict[str, int] = {}
    output: str = ""  # leaf plugin output
    acknowledged: bool = False
    in_downtime: bool = False
    is_flapping: bool = False
    # Distributed monitoring: the node's site went dead and this is its last
    # known state (per-site trust) — render greyed/stale, not healthy.
    stale: bool = False
    last_state_change: float | None = None  # leaf age for triage ("since…")
    # Distributed monitoring: leaf hosts carry their originating site.
    site_id: str | None = None
    # Per-host service-state counts, host leaves only — feeds the hover/drawer
    # service pills.
    services_summary: ServicesSummary | None = None
    # A host leaf's *own* state, where it differs from the roll-up in ``state``.
    # The tree colours a host by the worst of itself and its services, but a
    # drawer opened on that host must say UP, not the CRITICAL of a service it
    # merely carries. Only sent when the two differ, so the common case costs
    # nothing on a 100k-host tree.
    own_state: str | None = None
    children: list[FolderTreeNode] = []


class FolderTreeNodePatch(BaseModel):
    """Live-field update for one foldertree node, keyed by ``path``. Sent over SSE
    instead of the whole tree once a snapshot exists, so only changed nodes travel.
    ``children_order`` is set only when this node's child order changed (the tree
    sorts by severity, so a state flip can reorder siblings without any add/remove)."""

    path: str
    title: str
    site_id: str | None = None
    state: str
    is_empty: bool
    host_count: int
    problem_count: int
    severity_counts: dict[str, int]
    output: str
    acknowledged: bool
    in_downtime: bool
    is_flapping: bool
    stale: bool = False
    last_state_change: float | None = None
    services_summary: ServicesSummary | None = None
    own_state: str | None = None
    children_order: list[str] | None = None


class FolderTreeDelta(BaseModel):
    """SSE folder-tree update. ``full`` carries the whole tree (first tick or a
    structural add/remove/move); otherwise ``changed`` carries only the nodes whose
    fields or child order changed since the last tick."""

    full: bool
    tree: FolderTreeNode | None = None
    changed: list[FolderTreeNodePatch] = []


class FolderHostService(BaseModel):
    """One service of a host, fetched lazily when a foldertree host is expanded.

    Kept minimal: the frontend already knows the host (path/site) it drilled
    into, so it composes the full FolderTreeNode from this. Ordered by the
    endpoint worst-state first (CRITICAL on top).
    """

    name: str
    state: str
    output: str = ""
    acknowledged: bool = False
    in_downtime: bool = False
    is_flapping: bool = False
    last_state_change: float | None = None


class FolderServiceMatch(BaseModel):
    """A host together with the services that matched a folder-map service
    search. Grouped by host so the frontend injects the matched services into
    the already-loaded tree node (identified by host name + site)."""

    host: str
    site_id: str | None = None
    services: list[FolderHostService] = []


class FolderServiceSearchResult(BaseModel):
    """Result of a server-side (Livestatus) folder-map service search.

    Service searches can't be answered from the SSE tree (services aren't
    pushed, to scale to millions), so they hit Livestatus directly. ``truncated``
    is True when the result hit ``limit`` and more matches exist — surfaced in
    the UI so the cap is never silent."""

    matches: list[FolderServiceMatch] = []
    truncated: bool = False
    limit: int


class MapStates(BaseModel):
    map_name: str
    states: list[ObjectState]
    generated_at: float  # unix timestamp
    connection_ok: bool = True  # False when the monitoring connection is unreachable
    # Distributed monitoring: federation sites that stopped answering — their
    # objects (foldertree leaves) freeze on the last known state, marked stale.
    dead_sites: list[str] = []
    # Populated only for foldertree maps: the resolved + aggregated tree.
    folder_tree: FolderTreeNode | None = None
    # The knobs the producing daemon is running on. Required rather than
    # defaulted: the client drives its polling fallback off the cadence, so a
    # states payload that silently omitted it would leave the client guessing.
    runtime: DaemonRuntime
