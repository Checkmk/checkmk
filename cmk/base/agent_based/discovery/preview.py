#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Callable, Container, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.exceptions import OnError
from cmk.utils.labels import HostLabel, ServiceLabel
from cmk.utils.log import console
from cmk.utils.parameters import TimespecificParameters
from cmk.utils.rulesets.ruleset_matcher import RulesetName
from cmk.utils.type_defs import CheckPluginName, HostName, Item, SectionName, ServiceName

from cmk.automations.results import CheckPreviewEntry

from cmk.checkers import (
    FetcherFunction,
    HostKey,
    ParserFunction,
    PHostLabelDiscoveryPlugin,
    PSectionPlugin,
    SummarizerFunction,
)
from cmk.checkers.check_table import ConfiguredService, LegacyCheckParameters
from cmk.checkers.checkresults import ActiveCheckResult, ServiceCheckResult

import cmk.base.agent_based.checking as checking
import cmk.base.config as config
import cmk.base.core
from cmk.base.agent_based.data_provider import (
    filter_out_errors,
    make_providers,
    Provider,
    store_piggybacked_sections,
)
from cmk.base.agent_based.utils import check_parsing_errors
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.value_store import load_host_value_store, ValueStoreManager
from cmk.base.config import ConfigCache, ObjectAttributes
from cmk.base.core_config import get_active_check_descriptions

from ._host_labels import (
    analyse_cluster_labels,
    analyse_host_labels,
    discover_host_labels,
    do_load_labels,
)
from .autodiscovery import _Transition, get_host_services
from .utils import QualifiedDiscovery

__all__ = ["CheckPreview", "get_check_preview"]


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
    section_plugins: Mapping[SectionName, PSectionPlugin],
    host_label_plugins: Mapping[SectionName, PHostLabelDiscoveryPlugin],
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
    find_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
    ignored_services: Container[ServiceName],
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
    host_attrs = config_cache.get_host_attributes(host_name)

    fetched = fetcher(host_name, ip_address=ip_address)
    parsed = parser((f[0], f[1]) for f in fetched)

    host_sections_no_error = filter_out_errors(parser((f[0], f[1]) for f in fetched))
    store_piggybacked_sections(host_sections_no_error)
    providers = make_providers(host_sections_no_error, section_plugins)

    host_labels, kept_labels = (
        analyse_cluster_labels(
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
                on_error=on_error,
            ),
            ruleset_matcher=config_cache.ruleset_matcher,
            existing_host_labels=do_load_labels(host_name),
            save_labels=False,
        )
    )

    for result in check_parsing_errors(
        itertools.chain.from_iterable(resolver.parsing_errors for resolver in providers.values())
    ):
        for line in result.details:
            console.warning(line)

    grouped_services, _has_changes = get_host_services(
        host_name,
        config_cache=config_cache,
        providers=providers,
        check_plugins=check_plugins,
        find_service_description=find_service_description,
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
        table=[
            *passive_rows,
            *_active_check_preview_rows(
                host_name,
                config_cache.alias(host_name),
                config_cache.active_checks(host_name),
                ignored_services,
                host_attrs,
            ),
            *_custom_check_preview_rows(
                host_name, config_cache.custom_checks(host_name), ignored_services
            ),
        ],
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
        str(check_plugin.check_ruleset_name)
        if check_plugin and check_plugin.check_ruleset_name
        else None
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


def _custom_check_preview_rows(
    host_name: HostName, custom_checks: list[dict], ignored_services: Container[ServiceName]
) -> Sequence[CheckPreviewEntry]:
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


def _active_check_preview_rows(
    host_name: HostName,
    alias: str,
    active_checks: list[tuple[str, list[Any]]],
    ignored_services: Container[ServiceName],
    host_attrs: ObjectAttributes,
) -> Sequence[CheckPreviewEntry]:
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
