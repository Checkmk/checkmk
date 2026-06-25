#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG002  # The interface's no-op defaults keep the full signature

"""Abstract monitoring connection interface."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import NotRequired, TYPE_CHECKING, TypedDict

from cmk.maps.backend.schemas.state import ObjectDetails, ObjectState, ServicesSummary

if TYPE_CHECKING:
    from cmk.maps.backend.integrations.checkmk import FolderScope


class TopologyRow(TypedDict):
    """One host in the topology view (parent-child flow-graph).

    Carries the same status-detail fields as ``ObjectState`` so the FlowMap
    tooltip can display the same information as the static-map tooltip without
    a second round-trip. Optional fields are omitted by connections that don't
    populate them (the frontend treats missing as unknown).

    ``site_id`` is set in distributed Checkmk setups; other connections omit it.
    """

    name: str
    parents: list[str]
    state: str
    output: str
    site_id: NotRequired[str | None]
    alias: NotRequired[str]
    address: NotRequired[str]
    acknowledged: NotRequired[bool]
    in_downtime: NotRequired[bool]
    notifications_enabled: NotRequired[bool]
    active_checks_enabled: NotRequired[bool]
    last_check: NotRequired[float | None]
    next_check: NotRequired[float | None]
    last_state_change: NotRequired[float | None]
    state_type: NotRequired[str]
    current_attempt: NotRequired[int]
    max_attempts: NotRequired[int]
    services_summary: NotRequired[ServicesSummary | None]


def topology_problem_rank(row: TopologyRow) -> int:
    """CRIT-weighted rank for top-K host selection.

    Critical scores higher than warning so a single CRIT outranks several
    WARNs; unknown/pending fall in between. Used by both the REST endpoint
    and the background warmup loop so they pick the same top-K hosts.
    """
    s = row.get("services_summary")
    if s is None:
        return 0
    return int(s.critical * 4 + s.warning * 2 + s.unknown * 2 + s.pending)


class GeoHost(TypedDict):
    """A host with discovered geo-coordinates.

    Used by the worldmap-map automap source to populate hosts dynamically
    from monitoring custom variables (``_LATITUDE``/``_LONGITUDE`` etc.) so
    operators don't have to maintain a parallel coordinate list manually.
    """

    name: str
    alias: str
    lat: float
    lng: float


class ServiceRow(TypedDict):
    """One service attached to a host (used by get_host_services / batch APIs).

    name/state/output are required — the rest are optional context fields surfaced
    in the hover/context UI so operators don't have to drill into Checkmk just to
    see acknowledged/in_downtime/last-state-change.
    """

    name: str
    state: str
    output: str
    acknowledged: NotRequired[bool]
    in_downtime: NotRequired[bool]
    is_flapping: NotRequired[bool]
    notifications_enabled: NotRequired[bool]
    last_state_change: NotRequired[float | None]
    last_check: NotRequired[float | None]
    next_check: NotRequired[float | None]


class ServiceMatchRow(TypedDict):
    """One (host, service) hit from a folder-map service search.

    Like ``ServiceRow`` but carries the owning host + site so the frontend can
    place the match into the already-loaded folder tree without a second query.
    """

    host_name: str
    name: str
    state: str
    output: str
    site_id: NotRequired[str | None]
    acknowledged: NotRequired[bool]
    in_downtime: NotRequired[bool]
    is_flapping: NotRequired[bool]
    last_state_change: NotRequired[float | None]


class FolderInfo(TypedDict):
    """One WATO/SETUP folder for a foldertree map.

    ``path`` is the normalised folder path ("" = root, e.g. "datacenters/muc").
    ``folder_id`` is the stable WATO ``__id`` when known (survives rename/move);
    empty when only the Livestatus slug path is available.
    """

    path: str
    title: str
    folder_id: NotRequired[str]
    # Effective read-permitted contact groups (own + inherited via recurse_perms),
    # mirroring Checkmk folder permissions. Empty = only see-all users may read it.
    # User-independent, so it can be cached with the folder structure.
    permitted_groups: NotRequired[list[str]]
    # Resolved for the requesting user: True when they may see this folder
    # (see-all, or a member of one of ``permitted_groups``). Set per request.
    permitted: NotRequired[bool]


class FolderTreeHostRow(TypedDict):
    """One host placed in the folder tree, with the state context needed to
    bubble a folder's worst-state without a second round-trip."""

    host_name: str
    folder_path: str  # normalised ("" = root)
    state: str
    output: str
    site_id: NotRequired[str | None]
    acknowledged: NotRequired[bool]
    in_downtime: NotRequired[bool]
    is_flapping: NotRequired[bool]
    last_state_change: NotRequired[float | None]
    services_summary: NotRequired[ServicesSummary | None]
    # Per-site trust: the host's site went dead and this row is replayed from
    # the last successful fetch (livestatus connection-level cache).
    stale: NotRequired[bool]


@dataclass
class FolderTreeData:
    """Raw folder-tree data from a connection: the folder structure (incl. empty
    folders where the source can supply them) plus host rows tagged with their
    folder. Tree assembly + worst-state bubbling happen connection-agnostically
    in the state service."""

    folders: list[FolderInfo] = field(default_factory=list)
    hosts: list[FolderTreeHostRow] = field(default_factory=list)
    # Federation sites that stopped answering (their hosts above are the
    # replayed last-known rows, marked ``stale``).
    dead_sites: list[str] = field(default_factory=list)


@dataclass
class MetricHistoryResult:
    """Combined result of a metric history fetch.

    series: metric_id → list of (timestamp, value, unit) tuples
    titles: metric_id → display name, only when the backend itself supplies
        one (remote REST metric endpoint, demo connection). Registry titles
        and graph grouping are display semantics the client resolves via the
        GUI (the maps_metric_info endpoint), not here.
    """

    series: dict[str, list[tuple[float, float, str]]] = field(default_factory=dict)
    titles: dict[str, str] = field(default_factory=dict)


class ConnectionBase(ABC):
    """Base class all monitoring connections must implement."""

    connection_id: str = "unknown"

    @asynccontextmanager
    async def with_auth_user(self, username: str) -> AsyncIterator[None]:
        """Scope queries inside the block to *username*'s contact visibility.

        Default: no scoping — only connections with contact-based host
        visibility (Livestatus ``AuthUser``) override this.
        """
        yield

    @asynccontextmanager
    async def with_folder_scope(self, scope: FolderScope | None) -> AsyncIterator[None]:
        """Scope the SETUP folder skeleton to *scope*'s readable folders.

        Default: no scoping — only connections with a folder concept
        (Livestatus) override this. Independent of ``with_auth_user`` because
        folder-read permission and monitoring host visibility differ.
        """
        yield

    @abstractmethod
    async def get_host_state(self, hostname: str) -> ObjectState:
        """Return current state for a host."""
        ...

    @abstractmethod
    async def get_service_state(self, host: str, service: str) -> ObjectState:
        """Return current state for a service."""
        ...

    @abstractmethod
    async def get_hostgroup_states(self, group: str) -> ObjectState:
        """Return aggregated state for a host group (worst-state aggregation)."""
        ...

    @abstractmethod
    async def get_servicegroup_states(self, group: str) -> ObjectState:
        """Return aggregated state for a service group."""
        ...

    async def get_dyngroup_state(self, object_types: str, object_filter: str) -> ObjectState:
        """Return aggregated worst-state for hosts/services matched by a Livestatus filter.

        Default returns NOT_SUPPORTED — only connections that speak raw LQL
        (Livestatus) override this.
        """
        return ObjectState(object_id="", type="dyngroup", state="NOT_SUPPORTED")

    @abstractmethod
    async def get_objects(
        self, obj_type: str, host: str | None = None, search: str | None = None
    ) -> list[str]:
        """Return list of object names of given type (host/service/hostgroup/…).

        When *host* is given for ``obj_type == "service"`` the lookup is scoped
        to that host so large environments don't fetch every service. *search*
        is a case-insensitive substring applied server-side (CMK-style
        autocompleter) so huge sites filter+limit at the source instead of
        streaming every name to the client.
        """
        ...

    @abstractmethod
    async def get_group_members(self, group_type: str, group_name: str) -> list[str]:
        """Return member names for a radar filter (hostgroup/servicegroup/all_hosts/all_services)."""
        ...

    async def get_hosts_with_geo(
        self, *, group_type: str | None = None, group_name: str | None = None
    ) -> list[GeoHost]:
        """Return hosts that carry latitude/longitude custom variables.

        Default implementation returns nothing — only Livestatus exposes the
        custom_variable_names/values columns we need. ``group_type`` may be
        ``"hostgroup"``, ``"servicegroup"`` or ``None`` (all hosts); when set,
        ``group_name`` filters to that group.
        """
        return []

    async def get_folder_tree(
        self, *, only_hard: bool = False, sites: list[str] | None = None
    ) -> FolderTreeData:
        """Return SETUP folder structure + host rows for a foldertree map.

        Default returns nothing (connections without a folder concept, e.g.
        the demo/fake connection). Checkmk/Livestatus derives folders from the ``filename``
        column; ``sites`` (when given) scopes a federated query. Tree assembly
        and worst-state bubbling happen in the state service.
        """
        return FolderTreeData()

    async def search_services(
        self,
        *,
        host_terms: list[str],
        service_terms: list[str],
        any_terms: list[str],
        limit: int,
        only_hard: bool = False,
    ) -> list[ServiceMatchRow]:
        """Return (host, service) hits for a folder-map service search.

        All term lists are combined with AND (host/service scoped against the
        respective column; bare ``any_terms`` against host name OR description),
        filtered server-side and hard-capped at ``limit`` so a multi-million
        service site bounds the result at the source instead of streaming
        everything. Implementations should fetch ``limit + 1`` so the caller can
        tell a full page from a truncated one. Default: nothing (connections
        without a service search, e.g. the demo/fake connection).
        """
        return []

    @abstractmethod
    async def get_topology(self) -> list[TopologyRow]:
        """Return host topology as [{name, parents, state, output}] for flow map."""
        ...

    @abstractmethod
    async def get_host_services(self, hostname: str, only_hard: bool = False) -> list[ServiceRow]:
        """Return services for a host as [{name, state, output}].

        ``only_hard`` reports last hard states instead of current (soft) states,
        honouring a foldertree map's ``only_hard_states`` setting.
        """
        ...

    async def get_host_details(self, hostname: str) -> ObjectDetails | None:
        """Return on-demand drawer/property details for a host. Default: None."""
        return None

    async def get_service_details(self, hostname: str, service: str) -> ObjectDetails | None:
        """Return on-demand drawer/property details for a service. Default: None."""
        return None

    async def get_host_hard_state(self, hostname: str) -> ObjectState:
        """Return the last hard state for a host (default: delegates to current state)."""
        return await self.get_host_state(hostname)

    async def get_service_hard_state(self, host: str, service: str) -> ObjectState:
        """Return the last hard state for a service (default: delegates to current state)."""
        return await self.get_service_state(host, service)

    async def get_hosts_states(
        self, hostnames: list[str], only_hard: bool = False
    ) -> dict[str, ObjectState]:
        """Return states for multiple hosts. Result may be a partial dict (callers handle missing keys)."""
        results: dict[str, ObjectState] = {}
        for h in hostnames:
            results[h] = await (
                self.get_host_hard_state(h) if only_hard else self.get_host_state(h)
            )
        return results

    async def get_services_states(
        self, pairs: list[tuple[str, str]], only_hard: bool = False
    ) -> dict[tuple[str, str], ObjectState]:
        """Return states for multiple (host, service) pairs. Result may be a partial dict (callers handle missing keys)."""
        results: dict[tuple[str, str], ObjectState] = {}
        for host, svc in pairs:
            results[(host, svc)] = await (
                self.get_service_hard_state(host, svc)
                if only_hard
                else self.get_service_state(host, svc)
            )
        return results

    async def get_all_hosts_states(self, only_hard: bool = False) -> dict[str, ObjectState]:
        """Return states for ALL hosts on the connection.

        Default falls back to ``get_group_members`` + ``get_hosts_states``, which
        produces an O(n) Livestatus filter list for large setups. Connections with
        direct support (Livestatus) override this with a single unfiltered query.
        """
        hosts = await self.get_group_members("all_hosts", "")
        return await self.get_hosts_states(hosts, only_hard=only_hard)

    async def get_all_services_states(
        self, only_hard: bool = False
    ) -> dict[tuple[str, str], ObjectState]:
        """Return states for ALL services on the connection.

        Default falls back to ``get_group_members`` + ``get_services_states``;
        Livestatus overrides this with a single unfiltered query to avoid an
        O(n) filter explosion at large scale (e.g. >10k services).
        """
        members = await self.get_group_members("all_services", "")
        pairs: list[tuple[str, str]] = []
        for m in members:
            if ";" in m:
                host, svc = m.split(";", 1)
                pairs.append((host, svc))
        return await self.get_services_states(pairs, only_hard=only_hard)

    async def get_hosts_services_batch(self, hostnames: list[str]) -> dict[str, list[ServiceRow]]:
        """Return all services for multiple hosts.

        Default fan-out via ``asyncio.gather`` with a Semaphore so connections
        without a real bulk query (the demo/fake connection) still parallelise instead of
        serialising N round-trips. Livestatus overrides with a single grouped
        query — see ``LivestatusConnection.get_hosts_services_batch``.
        """
        if not hostnames:
            return {}
        sem = asyncio.Semaphore(20)

        async def _one(host: str) -> tuple[str, list[ServiceRow]]:
            async with sem:
                return host, await self.get_host_services(host)

        pairs = await asyncio.gather(*(_one(h) for h in hostnames))
        return dict(pairs)

    async def get_services_summary(self, hostnames: list[str]) -> dict[str, ServicesSummary]:
        """Return per-host service-state counts for the given hosts.

        Used by the host hover-tooltip to show pills like "12 OK · 2 WARN · 1 CRIT"
        without transporting the full service list. Default falls back to
        counting via ``get_host_services``; Livestatus overrides with a single
        grouped Stats query.
        """
        results: dict[str, ServicesSummary] = {}
        for h in hostnames:
            summary = ServicesSummary()
            for svc in await self.get_host_services(h):
                state = svc.get("state")
                if state == "OK":
                    summary.ok += 1
                elif state == "WARNING":
                    summary.warning += 1
                elif state == "CRITICAL":
                    summary.critical += 1
                elif state == "UNKNOWN":
                    summary.unknown += 1
                elif state == "PENDING":
                    summary.pending += 1
            results[h] = summary
        return results

    async def get_metric_history(
        self,
        host: str,
        service: str | None,
        start: int,
        end: int,
    ) -> MetricHistoryResult:
        """Return historical metric data as MetricHistoryResult.

        Default implementation returns empty result (not all connections support this).
        Checkmk/Livestatus connections override this using the rrddata column.
        """
        return MetricHistoryResult()

    @abstractmethod
    async def is_available(self) -> bool:
        """Check whether the connection is reachable."""
        ...
