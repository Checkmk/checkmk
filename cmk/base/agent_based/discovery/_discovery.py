#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import itertools
from collections import Counter
from collections.abc import Callable, Container, Iterable, Mapping, Sequence
from typing import Literal

import cmk.utils.paths
import cmk.utils.resulttype as result
from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.auto_queue import AutoQueue
from cmk.utils.exceptions import OnError
from cmk.utils.hostaddress import HostName
from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel
from cmk.utils.sectionname import SectionMap
from cmk.utils.servicename import ServiceName

from cmk.snmplib import SNMPRawData

from cmk.checkengine import (
    group_by_host,
    HostKey,
    ParserFunction,
    SectionPlugin,
    SourceInfo,
    SummarizerFunction,
)
from cmk.checkengine.check_table import ServiceID
from cmk.checkengine.checking import CheckPluginName, Item
from cmk.checkengine.checkresults import ActiveCheckResult
from cmk.checkengine.discovery import (
    analyse_cluster_labels,
    AutocheckServiceWithNodes,
    discover_host_labels,
    DiscoveryMode,
    DiscoveryPlugin,
    HostLabelPlugin,
    QualifiedDiscovery,
)
from cmk.checkengine.discovery.filters import ServiceFilter as _ServiceFilter
from cmk.checkengine.discovery.filters import ServiceFilters as _ServiceFilters
from cmk.checkengine.sectionparser import make_providers, store_piggybacked_sections
from cmk.checkengine.sectionparserutils import check_parsing_errors

from cmk.base.config import ConfigCache, DiscoveryCheckParameters

from .autodiscovery import get_host_services, ServicesByTransition

__all__ = ["execute_check_discovery"]


class _Transition(enum.Enum):
    NEW = enum.auto()
    VANISHED = enum.auto()

    @property
    def title(self) -> str:
        match self:
            case _Transition.NEW:
                return "Unmonitored"
            case _Transition.VANISHED:
                return "Vanished"

    def need_discovery(self, discovery_mode: DiscoveryMode) -> bool:
        return (
            self is _Transition.NEW
            and discovery_mode in (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH)
        ) or (
            self is _Transition.VANISHED
            and discovery_mode
            in (DiscoveryMode.REMOVE, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH)
        )


def execute_check_discovery(
    host_name: HostName,
    *,
    is_cluster: bool,
    cluster_nodes: Sequence[HostName],
    config_cache: ConfigCache,
    fetched: Iterable[tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception]]],
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    section_plugins: SectionMap[SectionPlugin],
    host_label_plugins: SectionMap[HostLabelPlugin],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    ignore_service: Callable[[HostName, ServiceName], bool],
    ignore_plugin: Callable[[HostName, CheckPluginName], bool],
    get_effective_host: Callable[[HostName, ServiceName], HostName],
    find_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
    enforced_services: Container[ServiceID],
) -> ActiveCheckResult:
    # Note: '--cache' is set in core_cmc, nagios template or even on CL and means:
    # 1. use caches as default:
    #    - Set FileCacheGlobals.maybe = True (set max_cachefile_age, else 0)
    #    - Set FileCacheGlobals.use_outdated = True
    # 2. Then these settings are used to read cache file or not
    params = config_cache.discovery_check_parameters(host_name)

    discovery_mode = DiscoveryMode(params.rediscovery.get("mode"))

    host_sections = parser(fetched)
    host_sections_by_host = group_by_host(
        (HostKey(s.hostname, s.source_type), r.ok) for s, r in host_sections if r.is_ok()
    )
    store_piggybacked_sections(host_sections_by_host)
    providers = make_providers(host_sections_by_host, section_plugins)

    if is_cluster:
        host_labels, _kept_labels = analyse_cluster_labels(
            host_name,
            cluster_nodes,
            discovered_host_labels={
                node_name: discover_host_labels(
                    node_name,
                    host_label_plugins,
                    providers=providers,
                    on_error=OnError.RAISE,
                )
                for node_name in cluster_nodes
            },
            existing_host_labels={
                node_name: DiscoveredHostLabelsStore(node_name).load()
                for node_name in cluster_nodes
            },
        )

    else:
        host_labels = QualifiedDiscovery[HostLabel](
            preexisting=DiscoveredHostLabelsStore(host_name).load(),
            current=discover_host_labels(
                host_name,
                host_label_plugins,
                providers=providers,
                on_error=OnError.RAISE,
            ),
        )

    services = get_host_services(
        host_name,
        is_cluster=is_cluster,
        cluster_nodes=cluster_nodes,
        providers=providers,
        plugins=plugins,
        ignore_service=ignore_service,
        ignore_plugin=ignore_plugin,
        get_effective_host=get_effective_host,
        get_service_description=find_service_description,
        enforced_services=enforced_services,
        on_error=OnError.RAISE,
    )

    services_result, services_need_rediscovery = _check_service_lists(
        host_name=host_name,
        services_by_transition=services,
        params=params,
        service_filters=_ServiceFilters.from_settings(params.rediscovery),
        discovery_mode=discovery_mode,
        find_service_description=find_service_description,
    )

    host_labels_result, host_labels_need_rediscovery = _check_host_labels(
        host_labels,
        params.severity_new_host_labels,
        discovery_mode,
    )

    parsing_errors_results = check_parsing_errors(
        itertools.chain.from_iterable(resolver.parsing_errors for resolver in providers.values())
    )

    return ActiveCheckResult.from_subresults(
        *itertools.chain(
            services_result,
            host_labels_result,
            (r for r in summarizer(host_sections) if r.state != 0),
            parsing_errors_results,
            [
                _schedule_rediscovery(
                    host_name,
                    is_cluster=is_cluster,
                    cluster_nodes=cluster_nodes,
                    need_rediscovery=(services_need_rediscovery or host_labels_need_rediscovery)
                    and all(r.state == 0 for r in parsing_errors_results),
                )
            ],
        )
    )


def _check_service_lists(
    *,
    host_name: HostName,
    services_by_transition: ServicesByTransition,
    params: DiscoveryCheckParameters,
    service_filters: _ServiceFilters,
    discovery_mode: DiscoveryMode,
    find_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
) -> tuple[Sequence[ActiveCheckResult], bool]:
    subresults = []
    need_rediscovery = False

    for transition, discovered_services, severity, service_filter in _iter_output_services(
        services_by_transition,
        params,
        service_filters,
    ):
        affected_check_plugins: Counter[CheckPluginName] = Counter()
        filtered = True

        for service, _found_on_nodes in discovered_services:
            affected_check_plugins[service.check_plugin_name] += 1
            filtered &= not service_filter(find_service_description(host_name, *service.id()))
            subresults.append(
                _make_active_check_result(
                    transition,
                    service.check_plugin_name,
                    service_description=find_service_description(host_name, *service.id()),
                )
            )

        if affected_check_plugins:
            info = ", ".join([f"{k}: {v}" for k, v in affected_check_plugins.items()])
            count = sum(affected_check_plugins.values())
            subresults.append(
                ActiveCheckResult(severity, f"{transition.title} services: {count} ({info})")
            )
            need_rediscovery |= not filtered and transition.need_discovery(discovery_mode)

    subresults.extend(
        _make_ignored_active_check_result(
            ignored_service.check_plugin_name,
            service_description=find_service_description(host_name, *ignored_service.id()),
        )
        for ignored_service, _found_on_nodes in services_by_transition.get("ignored", [])
    )
    if not any(s.summary for s in subresults):
        subresults.insert(0, ActiveCheckResult(0, "Services: all up to date"))
    return subresults, need_rediscovery


def _make_active_check_result(
    transition: _Transition, check_plugin_name: CheckPluginName, *, service_description: str
) -> ActiveCheckResult:
    return ActiveCheckResult(
        0,
        "",
        [f"{transition.title} service: {check_plugin_name}: {service_description}"],
    )


def _make_ignored_active_check_result(
    check_plugin_name: CheckPluginName, *, service_description: str
) -> ActiveCheckResult:
    return ActiveCheckResult(
        0,
        "",
        [f"Ignored service: {check_plugin_name}: {service_description}"],
    )


def _iter_output_services(
    services_by_transition: ServicesByTransition,
    params: DiscoveryCheckParameters,
    service_filters: _ServiceFilters,
) -> Iterable[tuple[_Transition, Sequence[AutocheckServiceWithNodes], int, _ServiceFilter,]]:
    yield (
        _Transition.NEW,
        services_by_transition.get("new", []),
        params.severity_new_services,
        service_filters.new,
    )
    yield (
        _Transition.VANISHED,
        services_by_transition.get("vanished", []),
        params.severity_vanished_services,
        service_filters.vanished,
    )


def _check_host_labels(
    host_labels: QualifiedDiscovery[HostLabel],
    severity_new_host_label: int,
    discovery_mode: DiscoveryMode,
) -> tuple[Sequence[ActiveCheckResult], bool]:
    subresults = []
    if host_labels.new:
        subresults.append(_make_labels_result("new", host_labels.new, severity_new_host_label))
    if host_labels.vanished:
        subresults.append(_make_labels_result("vanished", host_labels.vanished, 0))
    return (
        (
            subresults,
            discovery_mode in (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH),
        )
        if subresults
        else (
            [ActiveCheckResult(0, "Host labels: all up to date")],
            False,
        )
    )


def _make_labels_result(
    qualifier: Literal["new", "vanished"], labels: Sequence[HostLabel], severity: int
) -> ActiveCheckResult:
    plugin_count = Counter(l.plugin_name for l in labels)
    info = ", ".join(f"{key}: {count}" for key, count in plugin_count.items())
    return ActiveCheckResult(
        severity,
        f"{qualifier.capitalize()} host labels: {len(labels)} ({info})",
        [
            f"{qualifier.capitalize()} host label: {l.plugin_name}: {l.name}:{l.value}"
            for l in labels
        ],
    )


def _schedule_rediscovery(
    host_name: HostName,
    *,
    is_cluster: bool,
    cluster_nodes: Iterable[HostName],
    need_rediscovery: bool,
) -> ActiveCheckResult:
    if not need_rediscovery:
        return ActiveCheckResult()

    autodiscovery_queue = AutoQueue(cmk.utils.paths.autodiscovery_dir)
    if is_cluster:
        for nodename in cluster_nodes:
            autodiscovery_queue.add(nodename)
    else:
        autodiscovery_queue.add(host_name)

    return ActiveCheckResult(0, "rediscovery scheduled")
