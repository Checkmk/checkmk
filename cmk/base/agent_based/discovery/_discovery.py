#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence

import cmk.utils.paths
from cmk.utils.auto_queue import AutoQueue
from cmk.utils.exceptions import OnError
from cmk.utils.labels import HostLabel
from cmk.utils.type_defs import AgentRawData, HostName, Item, result, SectionName, ServiceName

from cmk.snmplib.type_defs import SNMPRawData

from cmk.checkers import (
    ParserFunction,
    PDiscoveryPlugin,
    PHostLabelDiscoveryPlugin,
    PSectionPlugin,
    SourceInfo,
    SummarizerFunction,
)
from cmk.checkers.checking import CheckPluginName
from cmk.checkers.checkresults import ActiveCheckResult
from cmk.checkers.sectionparser import filter_out_errors, make_providers, store_piggybacked_sections
from cmk.checkers.sectionparserutils import check_parsing_errors

from cmk.base.config import ConfigCache, DiscoveryCheckParameters

from ._filters import ServiceFilters as _ServiceFilters
from ._host_labels import analyse_host_labels, discover_host_labels, do_load_labels
from .autodiscovery import get_host_services, ServicesByTransition
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
    plugins: Mapping[CheckPluginName, PDiscoveryPlugin],
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

    host_labels = analyse_host_labels(
        host_name,
        discovered_host_labels=discover_host_labels(
            host_name,
            config_cache,
            host_label_plugins,
            providers=providers,
            on_error=OnError.RAISE,
        ),
        ruleset_matcher=config_cache.ruleset_matcher,
        existing_host_labels=do_load_labels(host_name),
        save_labels=False,
    )
    services = get_host_services(
        host_name,
        config_cache=config_cache,
        providers=providers,
        plugins=plugins,
        get_service_description=find_service_description,
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
            [host_labels_result],
            (r for r in summarizer(host_sections) if r.state != 0),
            parsing_errors_results,
            [
                _schedule_rediscovery(
                    host_name,
                    config_cache=config_cache,
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

    for transition, t_services, title, severity, service_filter in [
        (
            "new",
            services_by_transition.get("new", []),
            "unmonitored",
            params.severity_new_services,
            service_filters.new,
        ),
        (
            "vanished",
            services_by_transition.get("vanished", []),
            "vanished",
            params.severity_vanished_services,
            service_filters.vanished,
        ),
    ]:
        affected_check_plugin_names: Counter[CheckPluginName] = Counter()
        unfiltered = False

        for discovered_service, _found_on_nodes in t_services:
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
                        "%s: %s: %s"
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
        else:
            subresults.append(ActiveCheckResult(0, "", [f"No {title} services found"]))

    for discovered_service, _found_on_nodes in services_by_transition.get("ignored", []):
        subresults.append(
            ActiveCheckResult(
                0,
                "",
                [
                    "Ignored: %s: %s"
                    % (
                        discovered_service.check_plugin_name,
                        find_service_description(host_name, *discovered_service.id()),
                    )
                ],
            )
        )

    if not any(s.summary for s in subresults):
        subresults.insert(0, ActiveCheckResult(0, "All services up to date"))
    return subresults, need_rediscovery


def _check_host_labels(
    host_labels: QualifiedDiscovery[HostLabel],
    severity_new_host_label: int,
    discovery_mode: DiscoveryMode,
) -> tuple[ActiveCheckResult, bool]:
    return (
        (
            ActiveCheckResult(severity_new_host_label, f"New host labels: {len(host_labels.new)}"),
            discovery_mode in (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH),
        )
        if host_labels.new
        else (
            ActiveCheckResult(0, "All host labels up to date"),
            False,
        )
    )


def _schedule_rediscovery(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    need_rediscovery: bool,
) -> ActiveCheckResult:
    if not need_rediscovery:
        return ActiveCheckResult()

    autodiscovery_queue = AutoQueue(cmk.utils.paths.autodiscovery_dir)
    nodes = config_cache.nodes_of(host_name)
    if config_cache.is_cluster(host_name) and nodes:
        for nodename in nodes:
            autodiscovery_queue.add(nodename)
    else:
        autodiscovery_queue.add(host_name)

    return ActiveCheckResult(0, "rediscovery scheduled")
