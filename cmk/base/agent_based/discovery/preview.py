#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.exceptions import OnError
from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel, ServiceLabel
from cmk.utils.log import console
from cmk.utils.parameters import TimespecificParameters
from cmk.utils.rulesets.ruleset_matcher import RulesetName
from cmk.utils.type_defs import HostName, Item, SectionName, ServiceName

from cmk.automations.results import CheckPreviewEntry

from cmk.checkers import (
    CheckPlugin,
    DiscoveryPlugin,
    FetcherFunction,
    HostKey,
    ParserFunction,
    SectionPlugin,
    SummarizerFunction,
)
from cmk.checkers.check_table import ConfiguredService, LegacyCheckParameters
from cmk.checkers.checking import CheckPluginName
from cmk.checkers.checkresults import ActiveCheckResult, ServiceCheckResult
from cmk.checkers.discovery import (
    analyse_cluster_labels,
    discover_host_labels,
    HostLabelPlugin,
    QualifiedDiscovery,
)
from cmk.checkers.sectionparser import (
    filter_out_errors,
    make_providers,
    Provider,
    store_piggybacked_sections,
)
from cmk.checkers.sectionparserutils import check_parsing_errors

import cmk.base.agent_based.checking as checking
import cmk.base.config as config
import cmk.base.core
from cmk.base.api.agent_based.value_store import load_host_value_store, ValueStoreManager
from cmk.base.config import ConfigCache, get_active_check_descriptions

from .autodiscovery import _Transition, get_host_services

__all__ = [
    "CheckPreview",
    "get_check_preview",
    "get_active_check_preview_rows",
    "get_custom_check_preview_rows",
]


@dataclass(frozen=True)
class CheckPreview:
    table: Sequence[CheckPreviewEntry]
    labels: QualifiedDiscovery[HostLabel]
    source_results: Mapping[str, ActiveCheckResult]
    kept_labels: Mapping[HostName, Sequence[HostLabel]]


def get_check_preview(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    parser: ParserFunction,
    fetcher: FetcherFunction,
    summarizer: SummarizerFunction,
    section_plugins: Mapping[SectionName, SectionPlugin],
    host_label_plugins: Mapping[SectionName, HostLabelPlugin],
    discovery_plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
    find_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
    on_error: OnError,
) -> CheckPreview:
    """Get the list of service of a host or cluster and guess the current state of
    all services if possible"""
    ip_address = (
        None
        if config_cache.is_cluster(host_name)
        # We *must* do the lookup *before* calling `get_host_attributes()`
        # because...  I don't know... global variables I guess.  In any case,
        # doing it the other way around breaks one integration test.
        else config.lookup_ip_address(config_cache, host_name)
    )

    fetched = fetcher(host_name, ip_address=ip_address)
    parsed = parser((f[0], f[1]) for f in fetched)

    host_sections_no_error = filter_out_errors(parser((f[0], f[1]) for f in fetched))
    store_piggybacked_sections(host_sections_no_error)
    providers = make_providers(host_sections_no_error, section_plugins)

    if config_cache.is_cluster(host_name):
        host_labels, kept_labels = analyse_cluster_labels(
            host_name,
            config_cache.nodes_of(host_name) or (),
            discovered_host_labels={
                node_name: discover_host_labels(
                    node_name,
                    host_label_plugins,
                    providers=providers,
                    on_error=on_error,
                )
                for node_name in config_cache.nodes_of(host_name) or ()
            },
            existing_host_labels={
                node_name: DiscoveredHostLabelsStore(node_name).load()
                for node_name in config_cache.nodes_of(host_name) or ()
            },
        )
    else:
        host_labels = QualifiedDiscovery[HostLabel](
            preexisting=DiscoveredHostLabelsStore(host_name).load(),
            current=discover_host_labels(
                host_name,
                host_label_plugins,
                providers=providers,
                on_error=on_error,
            ),
        )
        kept_labels = {host_name: host_labels.kept()}

    for result in check_parsing_errors(
        itertools.chain.from_iterable(resolver.parsing_errors for resolver in providers.values())
    ):
        for line in result.details:
            console.warning(line)

    grouped_services = get_host_services(
        host_name,
        config_cache=config_cache,
        providers=providers,
        plugins=discovery_plugins,
        get_service_description=find_service_description,
        on_error=on_error,
    )

    with load_host_value_store(host_name, store_changes=False) as value_store_manager:
        passive_rows = [
            _check_preview_table_row(
                host_name,
                config_cache=config_cache,
                check_plugins=check_plugins,
                service=ConfiguredService(
                    check_plugin_name=entry.check_plugin_name,
                    item=entry.item,
                    description=find_service_description(host_name, *entry.id()),
                    parameters=config.compute_check_parameters(
                        host_name,
                        entry.check_plugin_name,
                        entry.item,
                        entry.parameters,
                    ),
                    discovered_parameters=entry.parameters,
                    service_labels={n: ServiceLabel(n, v) for n, v in entry.service_labels.items()},
                    is_enforced=True,
                ),
                check_source=check_source,
                providers=providers,
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
                check_plugins=check_plugins,
                check_source="manual",  # "enforced" would be nicer
                providers=providers,
                found_on_nodes=[host_name],
                value_store_manager=value_store_manager,
            )
            for _ruleset_name, service in config_cache.enforced_services_table(host_name).values()
        ]

    return CheckPreview(
        table=[*passive_rows],
        labels=host_labels,
        source_results={
            src.ident: result for (src, _sections), result in zip(parsed, summarizer(parsed))
        },
        kept_labels=kept_labels,
    )


def _check_preview_table_row(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    service: ConfiguredService,
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
    check_source: _Transition | Literal["manual"],
    providers: Mapping[HostKey, Provider],
    found_on_nodes: Sequence[HostName],
    value_store_manager: ValueStoreManager,
) -> CheckPreviewEntry:
    check_plugin = check_plugins.get(service.check_plugin_name)
    ruleset_name = (
        str(check_plugin.ruleset_name) if check_plugin and check_plugin.ruleset_name else None
    )

    result = (
        checking.get_aggregated_result(
            host_name,
            config_cache,
            providers,
            service,
            check_plugin,
            value_store_manager=value_store_manager,
            rtc_package=None,
        ).result
        if check_plugin is not None
        else ServiceCheckResult.check_not_implemented()
    )

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


def get_custom_check_preview_rows(
    config_cache: ConfigCache, host_name: HostName
) -> Sequence[CheckPreviewEntry]:
    custom_checks = config_cache.custom_checks(host_name)
    ignored_services = config.IgnoredServices(config_cache, host_name)
    return list(
        {
            entry["service_description"]: _make_check_preview_entry(
                host_name=host_name,
                check_plugin_name="custom",
                item=entry["service_description"],
                description=entry["service_description"],
                check_source=(
                    "ignored_custom"
                    if entry["service_description"] in ignored_services
                    else "custom"
                ),
            )
            for entry in custom_checks
        }.values()
    )


def get_active_check_preview_rows(
    config_cache: ConfigCache,
    host_name: HostName,
) -> Sequence[CheckPreviewEntry]:
    alias = config_cache.alias(host_name)
    active_checks = config_cache.active_checks(host_name)
    host_attrs = config_cache.get_host_attributes(host_name)
    ignored_services = config.IgnoredServices(config_cache, host_name)
    return list(
        {
            descr: _make_check_preview_entry(
                host_name=host_name,
                check_plugin_name=plugin_name,
                item=descr,
                description=descr,
                check_source="ignored_active" if descr in ignored_services else "active",
                effective_parameters=params,
            )
            for plugin_name, entries in active_checks
            for params in entries
            for descr in get_active_check_descriptions(
                plugin_name,
                config.active_check_info[plugin_name],
                host_name,
                alias,
                host_attrs,
                params,
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
