#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Nutanix Prism special agent on the v4 API (Prism Central only)"""

import json
import logging
import sys
import threading
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from http import HTTPStatus
from typing import NamedTuple, Protocol, Self, TextIO

from pydantic import BaseModel, ValidationError

from cmk.plugins.prism.special_agent.session import base_url
from cmk.plugins.prism.special_agent.v4_client import (
    JsonObject,
    PrismV4Client,
    PrismV4Error,
)
from cmk.plugins.prism.v4_models import (
    Alert,
    ClusterRemoteSupport,
    DiskConfig,
    DiskStats,
    Host,
    HostStats,
    ListedDisk,
    ListedHost,
    Node,
    NodeConfig,
    NodeDisk,
    StorageContainer,
    StorageContainerStats,
    StorageContainerWithStats,
    V4Model,
    Vm,
    VmWithHostName,
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
# started just before the end of the budget can wait up to 15 s for the Retry-After of a 503
# on top (see v4_client.RETRY): 40 s + 15 s = 55 s. Waiting for the rate limits, also after a
# 429, ends with the budget.
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
    # Listed once for all fetchers. If the listing failed, fetch_hosts reports the error and
    # fetch_vms reports the VMs without host names.
    hosts: Sequence[JsonObject] | PrismV4Error = ()


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
    if isinstance(context.hosts, PrismV4Error):
        raise context.hosts
    by_cluster: dict[str | None, list[dict[str, object]]] = {}
    for host in context.hosts:
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


def _fields(model: type[BaseModel]) -> list[str]:
    return [f.alias or name for name, f in model.model_fields.items()]


CONTAINERS_PATH = "clustermgmt/v4.0/config/storage-containers"
CONTAINER_STATS_PATH = "clustermgmt/v4.0/stats/storage-containers"
# Prism Central computes the dedup ratio every 6 hours
CONTAINER_STATS_WINDOW = timedelta(hours=12)
CONTAINER_STATS_SAMPLING = timedelta(hours=1)


def _parse_valid[M: V4Model](
    model: type[M],
    raw_entities: Iterable[JsonObject],
    what: str,
    id_key: str,
    messages: AgentMessages,
) -> list[M]:
    entities: list[M] = []
    for raw in raw_entities:
        try:
            entities.append(model.model_validate(raw))
        except ValidationError as e:
            fields = ", ".join(".".join(map(str, error["loc"])) for error in e.errors())
            name = raw.get("name") or raw.get(id_key)
            entity = f"{what} '{name}'" if name else f"a {what} without a name"
            messages.add_info(f"Skipped {entity}: Prism Central reports no valid {fields} for it")
    return entities


# The rate limits of the client set the pace, this only bounds the calls in flight: shared by
# all fetchers and together with their own calls it stays within the 10 connections requests
# keeps open per host, and still reaches 10 calls per second at 0.6 s per call
STATS_WORKERS = 6
_STATS_CALLS = threading.BoundedSemaphore(STATS_WORKERS)


def _fetch_each[T, R](items: Sequence[T], fetch_one: Callable[[T], R]) -> list[R]:
    """One call per item, in parallel

    The first call goes before the other calls of the batch (other fetchers may be calling
    meanwhile): it learns the rate limit of its endpoint, and if it fails, the others would
    fail the same way one after another.
    """

    def bounded(item: T) -> R:
        with _STATS_CALLS:
            return fetch_one(item)

    if not items:
        return []
    first = bounded(items[0])
    pool = ThreadPoolExecutor(max_workers=STATS_WORKERS)
    try:
        futures = [pool.submit(bounded, item) for item in items[1:]]
        return [first, *(future.result() for future in futures)]
    finally:
        # After an error, the calls not started yet would only fail the same way
        pool.shutdown(cancel_futures=True)


def _container_stats(
    context: FetchContext, container: StorageContainer
) -> StorageContainerStats | None:
    """None if the container was deleted since it was listed"""
    try:
        return StorageContainerStats.model_validate(
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
        LOGGER.info(
            "container %(name)s no longer exists: %(error)s",
            {"name": container.name, "error": e},
        )
        return None


def fetch_containers(context: FetchContext) -> Sequence[Section]:
    """A container that is gone, doesn't fit the model or has no usage stats is left out,
    the others are reported"""
    containers = _parse_valid(
        StorageContainer,
        context.client.list_all(
            CONTAINERS_PATH,
            {"$select": ",".join(_fields(StorageContainer))},
        ),
        "storage container",
        "containerExtId",
        context.messages,
    )
    if not containers:
        return []
    all_stats = _fetch_each(containers, partial(_container_stats, context))
    if all(stats is None for stats in all_stats):
        # Deletions don't hit every container at once, the stats endpoint itself is missing
        raise PrismV4Error("Prism Central returned 404 for the stats of every storage container")

    by_cluster: dict[str, list[dict[str, object]]] = {}
    for container, stats in zip(containers, all_stats, strict=True):
        if stats is None:
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
    return [
        Section("prism_containers_v2", cluster_containers, context.routing.host_for(cluster_id))
        for cluster_id, cluster_containers in by_cluster.items()
    ]


def fetch_remote_support(context: FetchContext) -> Sequence[Section]:
    """Reads the cluster list, so it makes no call of its own. Prism Central lists itself
    as a cluster, so its own state goes to the Prism Central host."""
    return [
        Section(
            "prism_remote_support_v2",
            ClusterRemoteSupport.model_validate(cluster).to_section(),
            context.routing.host_for(ext_id)
            if isinstance(ext_id := cluster.get("extId"), str)
            else Unroutable("clusters without an ID"),
        )
        for cluster in context.clusters
    ]


AHV_VMS_PATH = "vmm/v4.0/ahv/config/vms"
ESXI_VMS_PATH = "vmm/v4.0/esxi/config/vms"
# The same fields for AHV and ESXi VMs
VM_SELECT = "extId,name,powerState,description,memorySizeBytes,host/extId,cluster/extId"


def _host_names(hosts: Sequence[JsonObject] | PrismV4Error) -> dict[str, str]:
    if isinstance(hosts, PrismV4Error):
        return {}
    return {
        ext_id: host_name
        for host in hosts
        if isinstance(ext_id := host.get("extId"), str)
        and isinstance(host_name := host.get("hostName"), str)
    }


def _esxi_vms(context: FetchContext) -> list[JsonObject]:
    """The AHV VMs are reported even if Prism Central can't list the ESXi VMs"""
    try:
        return context.client.list_all(ESXI_VMS_PATH, {"$select": VM_SELECT})
    except PrismV4Error as e:
        if e.status == HTTPStatus.NOT_FOUND:
            context.messages.add_info(f"Could not fetch the ESXi VMs: {e}")
        else:
            context.messages.add_warning(f"Could not fetch the ESXi VMs: {e}")
        return []


def fetch_vms(context: FetchContext) -> Sequence[Section]:
    """A VM that doesn't fit the model is left out, the others are reported"""
    vms = _parse_valid(
        Vm,
        [*context.client.list_all(AHV_VMS_PATH, {"$select": VM_SELECT}), *_esxi_vms(context)],
        "VM",
        "extId",
        context.messages,
    )
    if not vms:
        return []
    host_names = _host_names(context.hosts)

    by_cluster: dict[str, list[dict[str, object]]] = {}
    for vm in vms:
        by_cluster.setdefault(vm.cluster.ext_id, []).append(
            VmWithHostName(
                extId=vm.ext_id,
                name=vm.name,
                powerState=vm.power_state,
                description=vm.description,
                memorySizeBytes=vm.memory_size_bytes,
                hostName=None if vm.host is None else host_names.get(vm.host.ext_id),
            ).to_section()
        )
    return [
        Section("prism_vms_v2", cluster_vms, context.routing.host_for(cluster_id))
        for cluster_id, cluster_vms in by_cluster.items()
    ]


DISKS_PATH = "clustermgmt/v4.0/config/disks"
DISK_STATS_PATH = "clustermgmt/v4.0/stats/disks"
# Prism Central samples the host and disk stats every 30 s and publishes them about 90 s late
NODE_STATS_WINDOW = timedelta(minutes=5)
NODE_STATS_SAMPLING = timedelta(seconds=30)


def _host_stats(context: FetchContext, host: ListedHost) -> HostStats | None:
    """None if the host has no cluster or is gone since it was listed"""
    if host.cluster is None:
        return None
    try:
        return HostStats.model_validate(
            context.client.entity_stats(
                f"clustermgmt/v4.0/stats/clusters/{host.cluster.uuid}/hosts/{host.ext_id}",
                window=NODE_STATS_WINDOW,
                sampling_interval=NODE_STATS_SAMPLING,
                select=_fields(HostStats),
            )
        )
    except PrismV4Error as e:
        if e.status != HTTPStatus.NOT_FOUND:
            raise
        LOGGER.info(
            "host %(name)s no longer exists: %(error)s", {"name": host.host_name, "error": e}
        )
        return None


def _disk_stats(context: FetchContext, disk: ListedDisk) -> DiskStats:
    """No stats if the disk is gone since it was listed"""
    try:
        return DiskStats.model_validate(
            context.client.entity_stats(
                f"{DISK_STATS_PATH}/{disk.ext_id}",
                window=NODE_STATS_WINDOW,
                sampling_interval=NODE_STATS_SAMPLING,
            )
        )
    except PrismV4Error as e:
        if e.status != HTTPStatus.NOT_FOUND:
            raise
        LOGGER.info("disk %(id)s no longer exists: %(error)s", {"id": disk.ext_id, "error": e})
        return DiskStats()


def _all_disk_stats(context: FetchContext, disks: Sequence[ListedDisk]) -> list[DiskStats]:
    """Only the storage tier summary needs them, so a failure loses only that"""
    try:
        return _fetch_each(disks, partial(_disk_stats, context))
    except PrismV4Error as e:
        context.messages.add_warning(f"Could not fetch the disk stats: {e}")
        return [DiskStats() for _disk in disks]


def fetch_nodes(context: FetchContext) -> Sequence[Section]:
    """Each host goes to a piggyback host of its own name, with its stats and disks"""
    if isinstance(context.hosts, PrismV4Error):
        raise context.hosts
    listed_hosts = [ListedHost.model_validate(host) for host in context.hosts]
    all_stats = _fetch_each(listed_hosts, partial(_host_stats, context))
    if any(host.cluster for host in listed_hosts) and all(stats is None for stats in all_stats):
        # Deletions don't hit every host at once, the stats endpoint itself is missing
        raise PrismV4Error("Prism Central returned 404 for the stats of every host")
    hosts = [
        (host, stats)
        for host, stats in zip(listed_hosts, all_stats, strict=True)
        if stats is not None
    ]
    host_ids = {host.ext_id for host, _stats in hosts}
    disks = [
        disk
        for raw in context.client.list_all(DISKS_PATH, {"$select": ",".join(_fields(ListedDisk))})
        if (disk := ListedDisk.model_validate(raw)).node_ext_id in host_ids
    ]

    disks_by_node: dict[str | None, list[NodeDisk]] = {}
    for disk, disk_stats in zip(disks, _all_disk_stats(context, disks), strict=True):
        disks_by_node.setdefault(disk.node_ext_id, []).append(
            NodeDisk(config=DiskConfig.model_validate(disk.to_section()), stats=disk_stats)
        )
    return [
        Section(
            "prism_host_v2",
            Node(
                config=NodeConfig.model_validate(host.to_section()),
                stats=stats,
                disks=disks_by_node.get(host.ext_id, []),
            ).to_section(),
            Unroutable("hosts without a name") if host.host_name is None else host.host_name,
        )
        for host, stats in hosts
    ]


SECTION_FETCHERS: Sequence[Fetcher] = (
    Fetcher("hosts", fetch_hosts),
    Fetcher("alerts", fetch_alerts),
    Fetcher("containers", fetch_containers),
    Fetcher("vms", fetch_vms),
    Fetcher("remote support", fetch_remote_support),
    Fetcher("nodes", fetch_nodes),
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
    hosts: Sequence[JsonObject] | PrismV4Error
    try:
        # No $select: it drops hypervisor/acropolisConnectionState (Prism Central 7.5)
        hosts = client.list_all(HOSTS_PATH)
    except PrismV4Error as e:
        if debug:
            raise
        hosts = e

    messages = AgentMessages()
    schedule = FetchSchedule(
        Storage(program_ident="agent_prism", host=hostname),
        key_prefix=f"{port}-{username}",
        clock=time.time,
    )
    result = run_fetchers(
        FetchContext(
            client, clusters, ClusterRouting.from_clusters(clusters, messages), messages, hosts
        ),
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
