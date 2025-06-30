#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import itertools
from collections import Counter
from collections.abc import Callable, Container, Iterable, Mapping, Sequence
from typing import Literal

import cmk.ccc.resulttype as result
from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostName

import cmk.utils.paths
from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.auto_queue import AutoQueue
from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel
from cmk.utils.log import console
from cmk.utils.sectionname import SectionMap, SectionName
from cmk.utils.servicename import ServiceName

from cmk.snmplib import SNMPRawData

from cmk.checkengine.checkresults import ActiveCheckResult
from cmk.checkengine.fetcher import HostKey, SourceInfo
from cmk.checkengine.parser import group_by_host, ParserFunction
from cmk.checkengine.plugins import AutocheckEntry, CheckPluginName, DiscoveryPlugin, ServiceID
from cmk.checkengine.sectionparser import make_providers, SectionPlugin, store_piggybacked_sections
from cmk.checkengine.sectionparserutils import check_parsing_errors
from cmk.checkengine.summarize import SummarizerFunction

from ._autochecks import (
    AutochecksConfig,
    AutocheckServiceWithNodes,
    AutochecksStore,
)
from ._autodiscovery import discovery_by_host, get_host_services_by_host_name, ServicesByTransition
from ._filters import ServiceFilter as _ServiceFilter
from ._filters import ServiceFilters as _ServiceFilters
from ._host_labels import analyse_cluster_labels, discover_host_labels, HostLabelPlugin
from ._params import DiscoveryCheckParameters
from ._utils import DiscoverySettings, QualifiedDiscovery

__all__ = ["execute_check_discovery"]


# TODO: remove this feature flag, once successfully tested
_CHANGED_PARAMS_FEATURE_FLAG = True


class _Transition(enum.Enum):
    NEW = enum.auto()
    VANISHED = enum.auto()
    CHANGED = enum.auto()

    @property
    def title(self) -> str:
        match self:
            case _Transition.NEW:
                return "unmonitored"
            case _Transition.VANISHED:
                return "vanished"
            case _Transition.CHANGED:
                return "changed"

    def need_discovery(self, discovery_mode: DiscoverySettings) -> bool:
        return (
            (self is _Transition.NEW and discovery_mode.add_new_services)
            or (self is _Transition.VANISHED and discovery_mode.remove_vanished_services)
            or (
                self is _Transition.CHANGED
                and (
                    discovery_mode.update_changed_service_parameters
                    or discovery_mode.update_changed_service_labels
                )
            )
        )


def execute_check_discovery(
    host_name: HostName,
    *,
    is_cluster: bool,
    cluster_nodes: Sequence[HostName],
    params: DiscoveryCheckParameters,
    fetched: Iterable[tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception]]],
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    section_plugins: SectionMap[SectionPlugin],
    host_label_plugins: SectionMap[HostLabelPlugin],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    autochecks_config: AutochecksConfig,
    section_error_handling: Callable[[SectionName, Sequence[object]], str],
    enforced_services: Container[ServiceID],
) -> Sequence[ActiveCheckResult]:
    # Note: '--cache' is set in core_cmc, nagios template or even on CL and means:
    # 1. use caches as default:
    #    - Set FileCacheGlobals.maybe = True (set max_cachefile_age, else 0)
    #    - Set FileCacheGlobals.use_outdated = True
    # 2. Then these settings are used to read cache file or not

    discovery_mode = DiscoverySettings.from_vs(params.rediscovery.get("mode"))

    host_sections = parser(fetched)
    host_sections_by_host = group_by_host(
        ((HostKey(s.hostname, s.source_type), r.ok) for s, r in host_sections if r.is_ok()),
        console.debug,
    )
    store_piggybacked_sections(host_sections_by_host, cmk.utils.paths.omd_root)
    providers = make_providers(
        host_sections_by_host,
        section_plugins,
        error_handling=section_error_handling,
    )

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

    services_by_host = get_host_services_by_host_name(
        host_name,
        existing_services=(
            {n: AutochecksStore(n).read() for n in cluster_nodes}
            if is_cluster
            else {host_name: AutochecksStore(host_name).read()}
        ),
        discovered_services=discovery_by_host(
            cluster_nodes if is_cluster else (host_name,), providers, plugins, OnError.RAISE
        ),
        is_cluster=is_cluster,
        cluster_nodes=cluster_nodes,
        autochecks_config=autochecks_config,
        enforced_services=enforced_services,
    )

    services_result, services_need_rediscovery = _check_service_lists(
        host_name=host_name,
        services_by_transition=services_by_host[host_name],
        params=params,
        service_filters=_ServiceFilters.from_settings(params.rediscovery),
        discovery_mode=discovery_mode,
        get_service_description=autochecks_config.service_description,
    )

    host_labels_result, host_labels_need_rediscovery = _check_host_labels(
        host_labels,
        params.severity_new_host_labels,
        discovery_mode,
    )

    parsing_errors_results = check_parsing_errors(
        itertools.chain.from_iterable(resolver.parsing_errors for resolver in providers.values())
    )
    failed_sources = [r for r in summarizer(host_sections) if r.state != 0]

    return [
        *itertools.chain(
            services_result,
            host_labels_result,
            failed_sources,
            parsing_errors_results,
            [
                _schedule_rediscovery(
                    host_name,
                    is_cluster=is_cluster,
                    cluster_nodes=cluster_nodes,
                    sources_failed=bool(failed_sources),
                    need_rediscovery=(services_need_rediscovery or host_labels_need_rediscovery)
                    and all(r.state == 0 for r in parsing_errors_results),
                )
            ],
        )
    ]


def _check_service_lists(
    *,
    host_name: HostName,
    services_by_transition: ServicesByTransition,
    params: DiscoveryCheckParameters,
    service_filters: _ServiceFilters,
    discovery_mode: DiscoverySettings,
    get_service_description: Callable[[HostName, AutocheckEntry], ServiceName],
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
            check_plugin_name = service.newer.check_plugin_name
            service_description = get_service_description(host_name, service.newer)
            service_result = _make_service_result(
                transition.title, check_plugin_name, service_description=service_description
            )

            affected_check_plugins[check_plugin_name] += 1
            filtered &= not service_filter(service_description)
            subresults.append(service_result)

        if affected_check_plugins:
            transition_result = _transition_result(transition, affected_check_plugins, severity)
            subresults.append(transition_result)
            need_rediscovery |= not filtered and transition.need_discovery(discovery_mode)

    change_affected_check_plugins: Counter[CheckPluginName] = Counter()
    filtered = True
    modified_labels = False
    modified_params = False
    for service, _found_on_nodes in services_by_transition.get("changed", []):
        modified = False
        check_plugin_name = service.newer.check_plugin_name
        service_description = get_service_description(host_name, service.newer)
        assert service.previous is not None and service.new is not None

        subresults.append(
            _make_service_result(
                _Transition.CHANGED.title,
                check_plugin_name,
                service_description=service_description,
            )
        )

        if service.new.service_labels != service.previous.service_labels:
            modified = True
            modified_labels = True
            filtered &= not service_filters.changed_labels(service_description)

        # TODO (params-discovery): we removed the params check for now as the front-end
        # implementation is yet to be done. See previous git history to see how the check was
        # implemented.
        if _CHANGED_PARAMS_FEATURE_FLAG and service.new.parameters != service.previous.parameters:
            modified = True
            modified_params = True
            filtered &= not service_filters.changed_params(service_description)

        if modified:
            change_affected_check_plugins[check_plugin_name] += 1

    if change_affected_check_plugins:
        severity = max(
            params.severity_changed_service_labels if modified_labels else 0,
            (
                params.severity_changed_service_params
                if _CHANGED_PARAMS_FEATURE_FLAG and modified_params
                else 0
            ),
        )
        subresults.append(
            _transition_result(_Transition.CHANGED, change_affected_check_plugins, severity)
        )
        need_rediscovery |= not filtered and _Transition.CHANGED.need_discovery(discovery_mode)

    subresults.extend(
        _make_service_result(
            "ignored",
            ignored_service.newer.check_plugin_name,
            service_description=get_service_description(host_name, ignored_service.newer),
        )
        for ignored_service, _found_on_nodes in services_by_transition.get("ignored", [])
    )
    if not any(s.summary for s in subresults):
        subresults.insert(0, ActiveCheckResult(state=0, summary="Services: all up to date"))
    return subresults, need_rediscovery


def _transition_result(
    transition: _Transition, affected_check_plugins: Counter, severity: int
) -> ActiveCheckResult:
    info = ", ".join([f"{k}: {v}" for k, v in affected_check_plugins.items()])
    count = sum(affected_check_plugins.values())
    if transition is _Transition.CHANGED and not _CHANGED_PARAMS_FEATURE_FLAG:
        # TODO: see above TODO (params-discovery)
        summary = f"Services with changed discovery labels: {count} ({info})"
    else:
        summary = f"Services {transition.title}: {count} ({info})"

    return ActiveCheckResult(state=severity, summary=summary)


def _make_service_result(
    transition_str: str, check_plugin_name: CheckPluginName, *, service_description: str
) -> ActiveCheckResult:
    return ActiveCheckResult(
        state=0,
        summary="",
        details=[f"Service {transition_str}: {check_plugin_name}: {service_description}"],
    )


def _iter_output_services(
    services_by_transition: ServicesByTransition,
    params: DiscoveryCheckParameters,
    service_filters: _ServiceFilters,
) -> Iterable[
    tuple[
        _Transition,
        Sequence[AutocheckServiceWithNodes],
        int,
        _ServiceFilter,
    ]
]:
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
    discovery_mode: DiscoverySettings,
) -> tuple[Sequence[ActiveCheckResult], bool]:
    subresults = []
    if host_labels.new:
        subresults.append(_make_labels_result("new", host_labels.new, severity_new_host_label))
    if host_labels.vanished:
        subresults.append(_make_labels_result("vanished", host_labels.vanished, 0))
    return (
        (
            subresults,
            discovery_mode.update_host_labels,
        )
        if subresults
        else (
            [ActiveCheckResult(state=0, summary="Host labels: all up to date")],
            False,
        )
    )


def _make_labels_result(
    qualifier: Literal["new", "vanished"], labels: Sequence[HostLabel], severity: int
) -> ActiveCheckResult:
    plugin_count = Counter(l.plugin_name for l in labels)
    info = ", ".join(f"{key}: {count}" for key, count in plugin_count.items())
    return ActiveCheckResult(
        state=severity,
        summary=f"{qualifier.capitalize()} host labels: {len(labels)} ({info})",
        details=[
            f"{qualifier.capitalize()} host label: {l.plugin_name}: {l.name}:{l.value}"
            for l in labels
        ],
    )


def _schedule_rediscovery(
    host_name: HostName,
    *,
    is_cluster: bool,
    cluster_nodes: Iterable[HostName],
    sources_failed: bool,
    need_rediscovery: bool,
) -> ActiveCheckResult:
    if not need_rediscovery:
        return ActiveCheckResult()

    if sources_failed:
        error_message = (
            "Automatic rediscovery currently not possible due to failing data source(s)."
            " Please run service discovery manually"
        )
        return ActiveCheckResult(state=1, summary=error_message)

    autodiscovery_queue = AutoQueue(cmk.utils.paths.autodiscovery_dir)
    if is_cluster:
        for nodename in cluster_nodes:
            autodiscovery_queue.add(nodename)
    else:
        autodiscovery_queue.add(host_name)

    return ActiveCheckResult(state=0, summary="Rediscovery scheduled")
