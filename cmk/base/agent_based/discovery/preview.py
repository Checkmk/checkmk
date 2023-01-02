#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence
from typing import Any, Literal

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.exceptions import OnError
from cmk.utils.log import console
from cmk.utils.parameters import TimespecificParameters
from cmk.utils.type_defs import AgentRawData, HostName, RulesetName, ServiceName
from cmk.utils.type_defs.result import Result

from cmk.automations.results import CheckPreviewEntry

from cmk.snmplib.type_defs import SNMPRawData

import cmk.checkers.cache
from cmk.checkers.cache import FileCacheOptions
from cmk.checkers.type_defs import Mode, NO_SELECTION, SourceInfo

import cmk.base.agent_based.checking as checking
import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_utils
import cmk.base.config as config
import cmk.base.core
import cmk.base.crash_reporting
from cmk.base.agent_based.data_provider import (
    make_broker,
    parse_messages,
    ParsedSectionsBroker,
    store_piggybacked_sections,
)
from cmk.base.agent_based.utils import check_parsing_errors
from cmk.base.api.agent_based.value_store import load_host_value_store, ValueStoreManager
from cmk.base.check_utils import ConfiguredService, LegacyCheckParameters
from cmk.base.config import ConfigCache, ObjectAttributes
from cmk.base.core_config import get_active_check_descriptions
from cmk.base.discovered_labels import HostLabel, ServiceLabel
from cmk.base.sources import fetch_all, make_sources

from ._discovery import get_host_services
from ._host_labels import analyse_host_labels
from .autodiscovery import _Transition
from .utils import QualifiedDiscovery

__all__ = ["get_check_preview"]


def get_check_preview(
    *,
    host_name: HostName,
    config_cache: ConfigCache,
    file_cache_options: FileCacheOptions,
    force_snmp_cache_refresh: bool,
    max_cachefile_age: cmk.checkers.cache.MaxAge,
    on_error: OnError,
) -> tuple[Sequence[CheckPreviewEntry], QualifiedDiscovery[HostLabel]]:
    """Get the list of service of a host or cluster and guess the current state of
    all services if possible"""
    ip_address = (
        None
        if config_cache.is_cluster(host_name)
        else config.lookup_ip_address(config_cache, host_name)
    )
    host_attrs = config_cache.get_host_attributes(host_name)

    # The code below this line is duplicated in automation_discovery()
    nodes = config_cache.nodes_of(host_name)
    if nodes is None:
        hosts = [(host_name, ip_address)]
    else:
        hosts = [(node, config.lookup_ip_address(config_cache, node)) for node in nodes]

    fetched: Sequence[
        tuple[SourceInfo, Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ] = fetch_all(
        *(
            make_sources(
                host_name_,
                ip_address_,
                config_cache=config_cache,
                force_snmp_cache_refresh=force_snmp_cache_refresh if nodes is None else False,
                selected_sections=NO_SELECTION,
                on_scan_error=on_error if nodes is None else OnError.RAISE,
                simulation_mode=config.simulation_mode,
                file_cache_options=file_cache_options,
                file_cache_max_age=max_cachefile_age,
            )
            for host_name_, ip_address_ in hosts
        ),
        mode=Mode.DISCOVERY,
    )
    host_sections, _source_results = parse_messages(
        config_cache,
        ((f[0], f[1]) for f in fetched),
        selected_sections=NO_SELECTION,
        keep_outdated=file_cache_options.keep_outdated,
        logger=logging.getLogger("cmk.base.discovery"),
    )
    store_piggybacked_sections(host_sections)
    parsed_sections_broker = make_broker(host_sections)
    # end of code duplication

    host_labels = analyse_host_labels(
        host_name=host_name,
        config_cache=config_cache,
        parsed_sections_broker=parsed_sections_broker,
        load_labels=True,
        save_labels=False,
        on_error=on_error,
    )

    for result in check_parsing_errors(parsed_sections_broker.parsing_errors()):
        for line in result.details:
            console.warning(line)

    grouped_services = get_host_services(
        host_name,
        config_cache=config_cache,
        parsed_sections_broker=parsed_sections_broker,
        on_error=on_error,
    )

    with load_host_value_store(host_name, store_changes=False) as value_store_manager:
        passive_rows = [
            _check_preview_table_row(
                host_name,
                config_cache=config_cache,
                service=ConfiguredService(
                    check_plugin_name=entry.check_plugin_name,
                    item=entry.item,
                    description=config.service_description(host_name, *entry.id()),
                    parameters=config.compute_check_parameters(
                        host_name,
                        entry.check_plugin_name,
                        entry.item,
                        entry.parameters,
                    ),
                    discovered_parameters=entry.parameters,
                    service_labels={n: ServiceLabel(n, v) for n, v in entry.service_labels.items()},
                ),
                check_source=check_source,
                parsed_sections_broker=parsed_sections_broker,
                found_on_nodes=found_on_nodes,
                value_store_manager=value_store_manager,
            )
            for check_source, services_with_nodes in grouped_services.items()
            for entry, found_on_nodes in services_with_nodes
        ] + [
            _check_preview_table_row(
                host_name,
                config_cache=config_cache,
                service=service,
                check_source="manual",  # "enforced" would be nicer
                parsed_sections_broker=parsed_sections_broker,
                found_on_nodes=[host_name],
                value_store_manager=value_store_manager,
            )
            for _ruleset_name, service in config_cache.enforced_services_table(host_name).values()
        ]

    return [
        *passive_rows,
        *_active_check_preview_rows(
            host_name,
            config_cache.alias(host_name),
            config_cache.active_checks(host_name),
            host_attrs,
        ),
        *_custom_check_preview_rows(host_name, config_cache.custom_checks(host_name)),
    ], host_labels


def _check_preview_table_row(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    service: ConfiguredService,
    check_source: _Transition | Literal["manual"],
    parsed_sections_broker: ParsedSectionsBroker,
    found_on_nodes: Sequence[HostName],
    value_store_manager: ValueStoreManager,
) -> CheckPreviewEntry:
    plugin = agent_based_register.get_check_plugin(service.check_plugin_name)
    ruleset_name = str(plugin.check_ruleset_name) if plugin and plugin.check_ruleset_name else None

    result = checking.get_aggregated_result(
        host_name,
        config_cache,
        parsed_sections_broker,
        service,
        plugin,
        value_store_manager=value_store_manager,
        rtc_package=None,
    ).result

    return _make_check_preview_entry(
        host_name=host_name,
        check_plugin_name=str(service.check_plugin_name),
        item=service.item,
        description=service.description,
        check_source=check_source,
        ruleset_name=ruleset_name,
        discovered_parameters=service.discovered_parameters,
        effective_parameters=service.parameters,
        exitcode=result.state,
        output=result.output,
        found_on_nodes=found_on_nodes,
        labels={l.name: l.value for l in service.service_labels.values()},
    )


def _custom_check_preview_rows(
    host_name: HostName, custom_checks: list[dict]
) -> Sequence[CheckPreviewEntry]:
    return list(
        {
            entry["service_description"]: _make_check_preview_entry(
                host_name=host_name,
                check_plugin_name="custom",
                item=entry["service_description"],
                description=entry["service_description"],
                check_source="ignored_custom"
                if config.service_ignored(host_name, None, description=entry["service_description"])
                else "custom",
            )
            for entry in custom_checks
        }.values()
    )


def _active_check_preview_rows(
    host_name: HostName,
    alias: str,
    active_checks: list[tuple[str, list[Any]]],
    host_attrs: ObjectAttributes,
) -> Sequence[CheckPreviewEntry]:
    return list(
        {
            descr: _make_check_preview_entry(
                host_name=host_name,
                check_plugin_name=plugin_name,
                item=descr,
                description=descr,
                check_source="ignored_active"
                if config.service_ignored(host_name, None, descr)
                else "active",
                effective_parameters=params,
            )
            for plugin_name, entries in active_checks
            for params in entries
            for descr in get_active_check_descriptions(
                host_name, alias, host_attrs, plugin_name, params
            )
        }.values()
    )


def _make_check_preview_entry(
    *,
    host_name: HostName,
    check_plugin_name: str,
    item: str | None,
    description: ServiceName,
    check_source: str,
    ruleset_name: RulesetName | None = None,
    discovered_parameters: LegacyCheckParameters = None,
    effective_parameters: LegacyCheckParameters | TimespecificParameters = None,
    exitcode: int | None = None,
    output: str = "",
    found_on_nodes: Sequence[HostName] | None = None,
    labels: dict[str, str] | None = None,
) -> CheckPreviewEntry:
    return CheckPreviewEntry(
        check_source=check_source,
        check_plugin_name=check_plugin_name,
        ruleset_name=ruleset_name,
        item=item,
        discovered_parameters=discovered_parameters,
        effective_parameters=_wrap_timespecific_for_preview(effective_parameters),
        description=description,
        state=exitcode,
        output=output
        or f"WAITING - {check_source.split('_')[-1].title()} check, cannot be done offline",
        # Service discovery never uses the perfdata in the check table. That entry
        # is constantly discarded, yet passed around(back and forth) as part of the
        # discovery result in the request elements. Some perfdata VALUES are not parsable
        # by ast.literal_eval such as "inf" it lead to ValueErrors. Thus keep perfdata empty
        metrics=[],
        labels=labels or {},
        found_on_nodes=[host_name] if found_on_nodes is None else list(found_on_nodes),
    )


def _wrap_timespecific_for_preview(
    params: LegacyCheckParameters | TimespecificParameters,
) -> LegacyCheckParameters:
    return (
        params.preview(cmk.base.core.timeperiod_active)
        if isinstance(params, TimespecificParameters)
        else params
    )
