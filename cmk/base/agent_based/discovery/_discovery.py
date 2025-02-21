#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Literal

import cmk.utils.paths
from cmk.utils.auto_queue import AutoQueue
from cmk.utils.exceptions import OnError
from cmk.utils.labels import HostLabel
from cmk.utils.type_defs import (
    AgentRawData,
    CheckPluginName,
    HostName,
    Item,
    result,
    SectionName,
    ServiceName,
)

from cmk.snmplib.type_defs import SNMPRawData

from cmk.checkers import (
    ParserFunction,
    PHostLabelDiscoveryPlugin,
    PSectionPlugin,
    SourceInfo,
    SummarizerFunction,
)
from cmk.checkers.checkresults import ActiveCheckResult

from cmk.base.agent_based.data_provider import (
    filter_out_errors,
    make_providers,
    store_piggybacked_sections,
)
from cmk.base.agent_based.utils import check_parsing_errors
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.config import ConfigCache, DiscoveryCheckParameters

from ._filters import ServiceFilter as _ServiceFilter
from ._filters import ServiceFilters as _ServiceFilters
from ._host_labels import (
    analyse_cluster_labels,
    analyse_host_labels,
    discover_host_labels,
    do_load_labels,
)
from .autodiscovery import AutocheckServiceWithNodes, get_host_services, ServicesByTransition
from .utils import DiscoveryMode, QualifiedDiscovery

__all__ = ["execute_check_discovery"]


def execute_check_discovery(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    fetched: Iterable[tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception]]],
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    section_plugins: Mapping[SectionName, PSectionPlugin],
    host_label_plugins: Mapping[SectionName, PHostLabelDiscoveryPlugin],
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
    find_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
) -> ActiveCheckResult:
    # Note: '--cache' is set in core_cmc, nagios template or even on CL and means:
    # 1. use caches as default:
    #    - Set FileCacheGlobals.maybe = True (set max_cachefile_age, else 0)
    #    - Set FileCacheGlobals.use_outdated = True
    # 2. Then these settings are used to read cache file or not
    params = config_cache.discovery_check_parameters(host_name)

    discovery_mode = DiscoveryMode(params.rediscovery.get("mode"))

    host_sections = parser(fetched)
    host_sections_no_error = filter_out_errors(host_sections)
    store_piggybacked_sections(host_sections_no_error)
    providers = make_providers(host_sections_no_error, section_plugins)

    host_labels, _kept_labels = (
        analyse_cluster_labels(
            host_name,
            config_cache.nodes_of(host_name) or (),
            discovered_host_labels={
                node_name: discover_host_labels(
                    node_name,
                    host_label_plugins,
                    providers=providers,
                    on_error=OnError.RAISE,
                )
                for node_name in config_cache.nodes_of(host_name) or ()
            },
            existing_host_labels={
                node_name: do_load_labels(node_name)
                for node_name in config_cache.nodes_of(host_name) or ()
            },
            ruleset_matcher=config_cache.ruleset_matcher,
        )
        if config_cache.is_cluster(host_name)
        else analyse_host_labels(
            host_name,
            discovered_host_labels=discover_host_labels(
                host_name,
                host_label_plugins,
                providers=providers,
                on_error=OnError.RAISE,
            ),
            ruleset_matcher=config_cache.ruleset_matcher,
            existing_host_labels=do_load_labels(host_name),
            save_labels=False,
        )
    )

    services, services_properties_have_changed = get_host_services(
        host_name,
        config_cache=config_cache,
        providers=providers,
        check_plugins=check_plugins,
        find_service_description=find_service_description,
        on_error=OnError.RAISE,
    )

    services_result, services_presence_has_changed = _check_service_lists(
        host_name=host_name,
        services_by_transition=services,
        params=params,
        service_filters=_ServiceFilters.from_settings(params.rediscovery),
        discovery_mode=discovery_mode,
        find_service_description=find_service_description,
    )
    services_need_rediscovery = services_presence_has_changed or (
        discovery_mode is DiscoveryMode.REFRESH and services_properties_have_changed
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

    return ActiveCheckResult.from_subresults(
        *itertools.chain(
            services_result,
            host_labels_result,
            failed_sources,
            parsing_errors_results,
            [
                _schedule_rediscovery(
                    host_name,
                    config_cache=config_cache,
                    sources_failed=bool(failed_sources),
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

    for transition, t_services, title, severity, service_filter in _iter_output_services(
        services_by_transition,
        params,
        service_filters,
    ):

        affected_check_plugin_names: Counter[CheckPluginName] = Counter()
        unfiltered = False

        for (discovered_service, _found_on_nodes) in t_services:
            affected_check_plugin_names[discovered_service.check_plugin_name] += 1

            if not unfiltered and service_filter(
                find_service_description(host_name, *discovered_service.id())
            ):
                unfiltered = True

            subresults.append(
                ActiveCheckResult(
                    0,
                    "",
                    [
                        "%s service: %s: %s"
                        % (
                            title.capitalize(),
                            discovered_service.check_plugin_name,
                            find_service_description(host_name, *discovered_service.id()),
                        )
                    ],
                )
            )

        if affected_check_plugin_names:
            info = ", ".join(["%s: %d" % e for e in affected_check_plugin_names.items()])
            count = sum(affected_check_plugin_names.values())
            subresults.append(
                ActiveCheckResult(severity, f"{title.capitalize()} services: {count} ({info})")
            )

            if unfiltered and (
                (
                    transition == "new"
                    and discovery_mode
                    in (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH)
                )
                or (
                    transition == "vanished"
                    and discovery_mode
                    in (DiscoveryMode.REMOVE, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH)
                )
            ):
                need_rediscovery = True

    for (discovered_service, _found_on_nodes) in services_by_transition.get("ignored", []):
        subresults.append(
            ActiveCheckResult(
                0,
                "",
                [
                    "Ignored service: %s: %s"
                    % (
                        discovered_service.check_plugin_name,
                        find_service_description(host_name, *discovered_service.id()),
                    )
                ],
            )
        )

    if not any(s.summary for s in subresults):
        subresults.insert(0, ActiveCheckResult(0, "Services: all up to date"))
    return subresults, need_rediscovery


def _iter_output_services(
    services_by_transition: ServicesByTransition,
    params: DiscoveryCheckParameters,
    service_filters: _ServiceFilters,
) -> Iterable[
    tuple[
        Literal["new", "vanished"],
        Sequence[AutocheckServiceWithNodes],
        str,
        int,
        _ServiceFilter,
    ]
]:
    yield (
        "new",
        services_by_transition.get("new", []),
        "unmonitored",
        params.severity_new_services,
        service_filters.new,
    )
    yield (
        "vanished",
        services_by_transition.get("vanished", []),
        "vanished",
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
    qualifier: str, labels: Sequence[HostLabel], severity: int
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
    config_cache: ConfigCache,
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
        return ActiveCheckResult(1, error_message)

    autodiscovery_queue = AutoQueue(cmk.utils.paths.autodiscovery_dir)
    nodes = config_cache.nodes_of(host_name)
    if config_cache.is_cluster(host_name) and nodes:
        for nodename in nodes:
            autodiscovery_queue.add(nodename)
    else:
        autodiscovery_queue.add(host_name)

    return ActiveCheckResult(0, "Rediscovery scheduled")
