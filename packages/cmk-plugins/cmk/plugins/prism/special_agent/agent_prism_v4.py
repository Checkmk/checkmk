#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Nutanix Prism special agent on the v4 API (Prism Central only)"""

import json
import logging
import sys
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from http import HTTPStatus
from typing import NamedTuple, Protocol, Self, TextIO

from pydantic import ValidationError

from cmk.plugins.prism.special_agent.session import base_url
from cmk.plugins.prism.special_agent.v4_client import (
    JsonObject,
    PrismV4Client,
    PrismV4Error,
)
from cmk.plugins.prism.v4_models import (
    Alert,
    Host,
    StorageContainer,
    StorageContainerStats,
    StorageContainerWithStats,
)
from cmk.server_side_programs.v1 import AgentMessages, Storage

LOGGER = logging.getLogger(__name__)

CLUSTERS_PATH = "clustermgmt/v4.0/config/clusters"
HOSTS_PATH = "clustermgmt/v4.0/config/hosts"
ALERTS_PATH = "monitoring/v4.0/serviceability/alerts"
ALERTS_QUERY = {
    "$filter": "isResolved eq false and isAcknowledged eq false",
    "$select": "severity,message,creationTime,parameters,clusterUUID,sourceEntity",
}

# The Checkmk service timeout (60 s by default) is shared with the other data sources. A call
# started just before the end of the budget can wait up to 15 s for Retry-After on top
# (see v4_client.RETRY): 40 s + 15 s = 55 s.
TIME_BUDGET = timedelta(seconds=40)
MAX_WORKERS = 4


@dataclass(frozen=True)
class Unroutable:
    reason: str


# None: the Prism Central host itself, str: a piggyback host
type Target = str | None | Unroutable


class Section(NamedTuple):
    name: str
    payload: object
    target: Target = None
    persist_until: int | None = None


@dataclass(frozen=True)
class ClusterRouting:
    """Cluster data goes to a piggyback host named after the cluster; Prism Central's
    own data stays on the Prism Central host."""

    targets: Mapping[str, Target]

    @classmethod
    def from_clusters(cls, clusters: Iterable[JsonObject], messages: AgentMessages) -> Self:
        targets: dict[str, Target] = {}
        by_name: dict[str, list[tuple[int, str]]] = {}
        for cluster in clusters:
            if not isinstance(ext_id := cluster.get("extId"), str):
                continue
            if _is_prism_central(cluster):
                targets[ext_id] = None
                continue
            name = str(cluster.get("name") or ext_id)
            by_name.setdefault(name, []).append((_incarnation(cluster), ext_id))
        for name, members in by_name.items():
            # The oldest cluster keeps the plain name, so adding a cluster never moves a host
            (_, oldest), *newer = sorted(members)
            targets[oldest] = name
            for _, ext_id in newer:
                targets[ext_id] = f"{name}-{ext_id}"
            if newer:
                hosts = ", ".join([name, *(f"{name}-{ext_id}" for _, ext_id in newer)])
                messages.add_info(f"Clusters named {name} are monitored as the hosts {hosts}")
        return cls(targets)

    def host_for(self, cluster_id: str) -> Target:
        return self.targets.get(cluster_id, Unroutable(f"unknown cluster {cluster_id}"))


def _incarnation(cluster: JsonObject) -> int:
    """When the cluster was created (µs), unknown ones count as newest"""
    config = cluster.get("config")
    incarnation = config.get("incarnationId") if isinstance(config, dict) else None
    return incarnation if isinstance(incarnation, int) else sys.maxsize


def _is_prism_central(cluster: JsonObject) -> bool:
    config = cluster.get("config")
    return isinstance(config, dict) and "PRISM_CENTRAL" in (config.get("clusterFunction") or [])


@dataclass(frozen=True)
class FetchContext:
    client: PrismV4Client
    clusters: Sequence[JsonObject]
    routing: ClusterRouting
    messages: AgentMessages


@dataclass(frozen=True)
class Fetcher:
    name: str
    fetch: Callable[[FetchContext], Sequence[Section]]
    # None: fetched on every run. Otherwise fetched when due, and Checkmk serves the
    # persisted sections in between. A run whose output Checkmk doesn't store ("Test agent
    # connection", cmk -d) still counts, so a new host may lack these sections for up to one
    # interval.
    refresh: timedelta | None = None


def _cluster_uuid(host: JsonObject) -> str | None:
    cluster = host.get("cluster")
    uuid = cluster.get("uuid") if isinstance(cluster, dict) else None
    return uuid if isinstance(uuid, str) else None


def fetch_hosts(context: FetchContext) -> Sequence[Section]:
    # No $select: it drops hypervisor/acropolisConnectionState (Prism Central 7.5)
    by_cluster: dict[str | None, list[dict[str, object]]] = {}
    for host in context.client.list_all(HOSTS_PATH):
        by_cluster.setdefault(_cluster_uuid(host), []).append(
            Host.model_validate(host).to_section()
        )
    return [
        Section(
            "prism_hosts_v2",
            hosts,
            Unroutable("hosts without a cluster")
            if cluster_id is None
            else context.routing.host_for(cluster_id),
        )
        for cluster_id, hosts in by_cluster.items()
    ]


def fetch_alerts(context: FetchContext) -> Sequence[Section]:
    # Every cluster gets a section, so its service turns OK once its alerts are gone
    by_target: dict[Target, list[dict[str, object]]] = {
        None: [],
        **{target: [] for target in context.routing.targets.values()},
    }
    for alert in context.client.list_all(ALERTS_PATH, ALERTS_QUERY):
        cluster_id = alert.get("clusterUUID")
        target = (
            context.routing.host_for(cluster_id)
            if isinstance(cluster_id, str)
            else Unroutable("alerts without a cluster")
        )
        by_target.setdefault(target, []).append(Alert.model_validate(alert).to_section())
    return [Section("prism_alerts_v2", alerts, target) for target, alerts in by_target.items()]


CONTAINERS_PATH = "clustermgmt/v4.0/config/storage-containers"
CONTAINER_STATS_PATH = "clustermgmt/v4.0/stats/storage-containers"
# Prism Central computes the dedup ratio every 6 hours
CONTAINER_STATS_WINDOW = timedelta(hours=12)
CONTAINER_STATS_SAMPLING = timedelta(hours=1)


def _fitting_containers(
    raw_containers: Iterable[JsonObject],
    messages: AgentMessages,
) -> list[StorageContainer]:
    containers: list[StorageContainer] = []
    for raw in raw_containers:
        try:
            containers.append(StorageContainer.model_validate(raw))
        except ValidationError as e:
            fields = ", ".join(".".join(map(str, error["loc"])) for error in e.errors())
            name = raw.get("name") or raw.get("containerExtId")
            container = (
                f"storage container '{name}'" if name else "a storage container without a name"
            )
            messages.add_info(
                f"Skipped {container}: Prism Central reports no valid {fields} for it"
            )
    return containers


def fetch_containers(context: FetchContext) -> Sequence[Section]:
    """A container that is gone, doesn't fit the model or has no usage stats is left out,
    the others are reported"""
    by_cluster: dict[str, list[dict[str, object]]] = {}
    containers = _fitting_containers(
        context.client.list_all(
            CONTAINERS_PATH,
            {
                "$select": ",".join(
                    f.alias or name for name, f in StorageContainer.model_fields.items()
                )
            },
        ),
        context.messages,
    )
    gone = 0
    for container in containers:
        try:
            stats = StorageContainerStats.model_validate(
                context.client.entity_stats(
                    f"{CONTAINER_STATS_PATH}/{container.container_ext_id}",
                    window=CONTAINER_STATS_WINDOW,
                    sampling_interval=CONTAINER_STATS_SAMPLING,
                )
            )
        except PrismV4Error as e:
            # Any other error concerns all containers, so the whole fetcher reports it once
            if e.status != HTTPStatus.NOT_FOUND:
                raise
            # Deleted since it was listed: left out without a warning, like a container the
            # legacy API no longer lists
            LOGGER.info(
                "container %(name)s no longer exists: %(error)s",
                {"name": container.name, "error": e},
            )
            gone += 1
            continue
        if not stats.has_usage:
            context.messages.add_info(
                f"Skipped storage container '{container.name}': "
                "Prism Central has no usage stats for it"
            )
            continue
        by_cluster.setdefault(container.cluster_ext_id, []).append(
            StorageContainerWithStats(
                name=container.name,
                cacheDeduplication=container.cache_deduplication,
                stats=stats,
            ).to_section()
        )
    if containers and gone == len(containers):
        # Deletions don't hit every container at once, the stats endpoint itself is missing
        raise PrismV4Error("Prism Central returned 404 for the stats of every storage container")
    return [
        Section("prism_containers_v2", cluster_containers, context.routing.host_for(cluster_id))
        for cluster_id, cluster_containers in by_cluster.items()
    ]


SECTION_FETCHERS: Sequence[Fetcher] = (
    Fetcher("hosts", fetch_hosts),
    Fetcher("alerts", fetch_alerts),
    Fetcher("containers", fetch_containers),
)


class TextStore(Protocol):
    """What FetchSchedule needs from cmk.server_side_programs.v1.Storage"""

    def read[T](self, key: str, default: T) -> str | T: ...

    def write(self, key: str, content: str) -> None: ...


class FetchSchedule:
    """Remembers when a fetcher with a refresh interval last succeeded"""

    def __init__(self, store: TextStore, key_prefix: str, clock: Callable[[], float]) -> None:
        self._store = store
        self._key_prefix = key_prefix
        self._clock = clock

    def _key(self, fetcher: Fetcher) -> str:
        return f"{self._key_prefix}-{fetcher.name}"

    def is_due(self, fetcher: Fetcher) -> bool:
        if fetcher.refresh is None:
            return True
        try:
            last = float(self._store.read(self._key(fetcher), ""))
        except ValueError:
            return True
        return not 0 <= self._clock() - last < fetcher.refresh.total_seconds()

    def persist_until(self, fetcher: Fetcher) -> int | None:
        if fetcher.refresh is None:
            return None
        # One spare interval, so a single failed refresh doesn't make the services stale
        return int(self._clock() + 2 * fetcher.refresh.total_seconds())

    def record(self, fetchers: Iterable[Fetcher]) -> None:
        """Call only once the output is written: a recorded fetcher is skipped until due"""
        now = str(self._clock())
        for fetcher in fetchers:
            if fetcher.refresh is not None:
                self._store.write(self._key(fetcher), now)


class FetchResult(NamedTuple):
    sections: Sequence[Section]
    succeeded: Sequence[Fetcher]


def run_fetchers(
    context: FetchContext,
    fetchers: Sequence[Fetcher],
    schedule: FetchSchedule,
    messages: AgentMessages,
    debug: bool,
) -> FetchResult:
    """A failing fetcher loses only its own sections"""
    due = [fetcher for fetcher in fetchers if schedule.is_due(fetcher)]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [(fetcher, pool.submit(fetcher.fetch, context)) for fetcher in due]

    sections: list[Section] = []
    succeeded: list[Fetcher] = []
    for fetcher, future in futures:
        try:
            fetched = future.result()
        except PrismV4Error as e:
            if debug:
                raise
            messages.add_warning(f"Could not fetch {fetcher.name}: {e}")
            continue
        except Exception as e:
            if debug:
                raise
            LOGGER.exception("fetcher %(name)s failed", {"name": fetcher.name})
            messages.add_warning(f"Could not fetch {fetcher.name}: {type(e).__name__}: {e}")
            continue
        persist_until = schedule.persist_until(fetcher)
        sections.extend(section._replace(persist_until=persist_until) for section in fetched)
        succeeded.append(fetcher)
    return FetchResult(sections, succeeded)


def write_sections(sections: Iterable[Section], stream: TextIO, messages: AgentMessages) -> None:
    by_host: dict[str | None, dict[str, Section]] = {}
    dropped: dict[str, set[str]] = {}
    for section in sections:
        if isinstance(section.target, Unroutable):
            dropped.setdefault(section.target.reason, set()).add(section.name)
            continue
        host_sections = by_host.setdefault(section.target, {})
        if section.name in host_sections:
            messages.add_warning(
                f"Dropped a second {section.name} section for {section.target or 'Prism Central'}"
            )
            continue
        host_sections[section.name] = section
    for reason, names in sorted(dropped.items()):
        messages.add_warning(f"Dropped {', '.join(sorted(names))}: {reason}")

    for section in by_host.pop(None, {}).values():
        _write_section(section, stream)
    for host, host_sections in by_host.items():
        stream.write(f"<<<<{host}>>>>\n")
        for section in host_sections.values():
            _write_section(section, stream)
        stream.write("<<<<>>>>\n")


def _write_section(section: Section, stream: TextIO) -> None:
    persist = "" if section.persist_until is None else f":persist({section.persist_until})"
    stream.write(f"<<<{section.name}:sep(0){persist}>>>\n{json.dumps(section.payload)}\n")


def agent_prism_v4_main(
    *,
    server: str,
    port: int,
    username: str,
    password: str,
    timeout: int,
    cert_check: bool | str,
    hostname: str,
    debug: bool,
    stream: TextIO,
) -> int:
    client = PrismV4Client(
        base_url(server, port),
        username,
        password,
        cert_check,
        timeout=timeout,
        deadline=time.monotonic() + TIME_BUDGET.total_seconds(),
    )
    try:
        clusters = client.list_all(CLUSTERS_PATH)
    except PrismV4Error as e:
        if debug:
            raise
        sys.stderr.write(f"Could not fetch the clusters from Prism Central: {e}\n")
        return 1
    LOGGER.info("got %(count)d clusters", {"count": len(clusters)})

    messages = AgentMessages()
    schedule = FetchSchedule(
        Storage(program_ident="agent_prism", host=hostname),
        key_prefix=f"{port}-{username}",
        clock=time.time,
    )
    result = run_fetchers(
        FetchContext(client, clusters, ClusterRouting.from_clusters(clusters, messages), messages),
        SECTION_FETCHERS,
        schedule,
        messages,
        debug,
    )
    write_sections(result.sections, stream, messages)
    stream.write(messages.render())
    stream.flush()
    schedule.record(result.succeeded)
    return 0
