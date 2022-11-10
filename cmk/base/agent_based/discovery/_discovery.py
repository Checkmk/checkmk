#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import Counter, Sequence, Tuple

import cmk.utils.paths
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.exceptions import OnError
from cmk.utils.type_defs import AgentRawData, CheckPluginName, HostName, result

from cmk.snmplib.type_defs import SNMPRawData

from cmk.core_helpers.type_defs import NO_SELECTION, SourceInfo

import cmk.base.config as config
from cmk.base.agent_based.data_provider import (
    make_broker,
    parse_messages,
    store_piggybacked_sections,
)
from cmk.base.agent_based.utils import check_parsing_errors, summarize_host_sections
from cmk.base.auto_queue import AutoQueue
from cmk.base.config import DiscoveryCheckParameters
from cmk.base.discovered_labels import HostLabel

from ._filters import ServiceFilters as _ServiceFilters
from ._host_labels import analyse_host_labels
from .autodiscovery import get_host_services, ServicesByTransition
from .utils import DiscoveryMode, QualifiedDiscovery

__all__ = ["execute_check_discovery"]


def execute_check_discovery(
    host_name: HostName,
    *,
    fetched: Sequence[
        Tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ],
) -> ActiveCheckResult:
    # Note: '--cache' is set in core_cmc, nagios template or even on CL and means:
    # 1. use caches as default:
    #    - Set FileCacheGlobals.maybe = True (set max_cachefile_age, else 0)
    #    - Set FileCacheGlobals.use_outdated = True
    # 2. Then these settings are used to read cache file or not

    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(host_name)
    params = host_config.discovery_check_parameters()

    discovery_mode = DiscoveryMode(params.rediscovery.get("mode"))

    host_sections, source_results = parse_messages(
        ((f[0], f[1]) for f in fetched),
        selected_sections=NO_SELECTION,
        logger=logging.getLogger("cmk.base.discovery"),
    )
    store_piggybacked_sections(host_sections)
    parsed_sections_broker = make_broker(host_sections)

    host_labels = analyse_host_labels(
        host_name=host_name,
        parsed_sections_broker=parsed_sections_broker,
        load_labels=True,
        save_labels=False,
        on_error=OnError.RAISE,
    )
    services = get_host_services(
        host_config,
        parsed_sections_broker,
        on_error=OnError.RAISE,
    )

    services_result, services_need_rediscovery = _check_service_lists(
        host_name=host_name,
        services_by_transition=services,
        params=params,
        service_filters=_ServiceFilters.from_settings(params.rediscovery),
        discovery_mode=discovery_mode,
    )

    host_labels_result, host_labels_need_rediscovery = _check_host_labels(
        host_labels,
        params.severity_new_host_labels,
        discovery_mode,
    )

    parsing_errors_results = check_parsing_errors(parsed_sections_broker.parsing_errors())

    return ActiveCheckResult.from_subresults(
        *services_result,
        host_labels_result,
        *summarize_host_sections(
            source_results=source_results,
            exit_spec_cb=host_config.exit_code_spec,
            time_settings_cb=lambda hostname: config.get_config_cache().get_piggybacked_hosts_time_settings(
                piggybacked_hostname=hostname,
            ),
            is_piggyback=host_config.is_piggyback_host,
        ),
        *parsing_errors_results,
        _schedule_rediscovery(
            host_name,
            need_rediscovery=(services_need_rediscovery or host_labels_need_rediscovery)
            and all(r.state == 0 for r in parsing_errors_results),
        ),
    )


def _check_service_lists(
    *,
    host_name: HostName,
    services_by_transition: ServicesByTransition,
    params: DiscoveryCheckParameters,
    service_filters: _ServiceFilters,
    discovery_mode: DiscoveryMode,
) -> Tuple[Sequence[ActiveCheckResult], bool]:

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

        for (discovered_service, _found_on_nodes) in t_services:
            affected_check_plugin_names[discovered_service.check_plugin_name] += 1

            if not unfiltered and service_filter(
                config.service_description(host_name, *discovered_service.id())
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
                            config.service_description(host_name, *discovered_service.id()),
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

    for (discovered_service, _found_on_nodes) in services_by_transition.get("ignored", []):
        subresults.append(
            ActiveCheckResult(
                0,
                "",
                [
                    "Ignored: %s: %s"
                    % (
                        discovered_service.check_plugin_name,
                        config.service_description(host_name, *discovered_service.id()),
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
) -> Tuple[ActiveCheckResult, bool]:
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
    need_rediscovery: bool,
) -> ActiveCheckResult:
    if not need_rediscovery:
        return ActiveCheckResult()

    autodiscovery_queue = AutoQueue(cmk.utils.paths.autodiscovery_dir)
    config_cache = config.get_config_cache()
    nodes = config_cache.nodes_of(host_name)
    if config_cache.is_cluster(host_name) and nodes:
        for nodename in nodes:
            autodiscovery_queue.add(nodename)
    else:
        autodiscovery_queue.add(host_name)

    return ActiveCheckResult(0, "rediscovery scheduled")
