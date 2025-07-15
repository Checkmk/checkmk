#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from cmk.ccc import tty
from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostAddress, HostName

import cmk.utils.paths
from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel
from cmk.utils.log import console
from cmk.utils.sectionname import SectionMap, SectionName
from cmk.utils.servicename import Item
from cmk.utils.timeperiod import timeperiod_active

from cmk.checkengine.checkresults import (
    ActiveCheckResult,
    MetricTuple,
    SubmittableServiceCheckResult,
)
from cmk.checkengine.fetcher import FetcherFunction, HostKey
from cmk.checkengine.parameters import TimespecificParameters, TimespecificParametersPreview
from cmk.checkengine.parser import group_by_host, ParserFunction
from cmk.checkengine.plugins import (
    AutocheckEntry,
    CheckerPlugin,
    CheckPluginName,
    ConfiguredService,
    DiscoveryPlugin,
    ServiceID,
)
from cmk.checkengine.sectionparser import (
    make_providers,
    Provider,
    SectionPlugin,
    store_piggybacked_sections,
)
from cmk.checkengine.sectionparserutils import check_parsing_errors
from cmk.checkengine.summarize import SummarizerFunction

from ._autochecks import AutochecksConfig, AutochecksStore
from ._autodiscovery import _Transition, discovery_by_host, get_host_services_by_host_name
from ._host_labels import analyse_cluster_labels, discover_host_labels, HostLabelPlugin
from ._utils import QualifiedDiscovery

__all__ = ["CheckPreview", "CheckPreviewEntry", "get_check_preview"]


@dataclass(frozen=True)
class CheckPreviewEntry:
    check_source: str
    check_plugin_name: str
    ruleset_name: str | None
    discovery_ruleset_name: str | None
    item: Item
    old_discovered_parameters: Mapping[str, object]
    new_discovered_parameters: Mapping[str, object]
    effective_parameters: TimespecificParametersPreview | Mapping[str, object]
    description: str
    state: int | None
    output: str
    # Service discovery never uses the perfdata in the check table. That entry
    # is constantly discarded, yet passed around(back and forth) as part of the
    # discovery result in the request elements. Some perfdata VALUES are not parsable
    # by ast.literal_eval such as "inf" it lead to ValueErrors. Thus keep perfdata empty
    metrics: list[MetricTuple]
    old_labels: Mapping[str, str]
    new_labels: Mapping[str, str]
    found_on_nodes: list[HostName]


@dataclass(frozen=True)
class CheckPreview:
    table: Mapping[HostName, Sequence[CheckPreviewEntry]]
    labels: QualifiedDiscovery[HostLabel]
    source_results: Mapping[str, ActiveCheckResult]
    kept_labels: Mapping[HostName, Sequence[HostLabel]]


def get_check_preview(
    host_name: HostName,
    ip_address: HostAddress | None,
    *,
    is_cluster: bool,
    cluster_nodes: Sequence[HostName],
    parser: ParserFunction,
    fetcher: FetcherFunction,
    summarizer: SummarizerFunction,
    section_plugins: SectionMap[SectionPlugin],
    section_error_handling: Callable[[SectionName, Sequence[object]], str],
    host_label_plugins: SectionMap[HostLabelPlugin],
    discovery_plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    check_plugins: Mapping[CheckPluginName, CheckerPlugin],
    autochecks_config: AutochecksConfig,
    compute_check_parameters: Callable[[HostName, AutocheckEntry], TimespecificParameters],
    enforced_services: Mapping[ServiceID, ConfiguredService],
    on_error: OnError,
) -> CheckPreview:
    """Get the list of service of a host or cluster and guess the current state of
    all services if possible. Those are for example (only?) displayed in the UI discovery page
    """

    fetched = fetcher(host_name, ip_address=ip_address)
    parsed = parser((f[0], f[1]) for f in fetched)

    host_sections = parser((f[0], f[1]) for f in fetched)
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
        host_labels, kept_labels = analyse_cluster_labels(
            host_name,
            cluster_nodes,
            discovered_host_labels={
                node_name: discover_host_labels(
                    node_name,
                    host_label_plugins,
                    providers=providers,
                    on_error=on_error,
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
                on_error=on_error,
            ),
        )
        kept_labels = {host_name: host_labels.present}

    for result in check_parsing_errors(
        itertools.chain.from_iterable(resolver.parsing_errors for resolver in providers.values())
    ):
        for line in result.details:
            console.warning(tty.format_warning(f"{line}"))

    grouped_services_by_host = get_host_services_by_host_name(
        host_name,
        existing_services=(
            {n: AutochecksStore(n).read() for n in cluster_nodes}
            if is_cluster
            else {host_name: AutochecksStore(host_name).read()}
        ),
        discovered_services=discovery_by_host(
            cluster_nodes if is_cluster else (host_name,), providers, discovery_plugins, on_error
        ),
        is_cluster=is_cluster,
        cluster_nodes=cluster_nodes,
        autochecks_config=autochecks_config,
        enforced_services=enforced_services,
    )

    passive_rows_by_host = {
        h: [
            _check_preview_table_row(
                h,
                check_plugins=check_plugins,
                service=ConfiguredService(
                    check_plugin_name=entry.newer.check_plugin_name,
                    item=entry.newer.item,
                    description=autochecks_config.service_description(h, entry.newer),
                    parameters=compute_check_parameters(h, entry.older),
                    discovered_parameters=entry.older.parameters,
                    labels=autochecks_config.service_labels(h, entry.older),
                    discovered_labels=entry.older.service_labels,
                    is_enforced=False,
                ),
                new_discovered_parameters=entry.newer.parameters,
                new_service_labels=entry.newer.service_labels,
                check_source=check_source,
                providers=providers,
                found_on_nodes=found_on_nodes,
            )
            for check_source, services_with_nodes in entries.items()
            for entry, found_on_nodes in services_with_nodes
        ]
        + [
            _check_preview_table_row(
                h,
                service=service,
                new_service_labels={},
                new_discovered_parameters={},
                check_plugins=check_plugins,
                check_source="manual",  # "enforced" would be nicer
                providers=providers,
                found_on_nodes=[h],
            )
            for service in enforced_services.values()
        ]
        for h, entries in grouped_services_by_host.items()
    }
    return CheckPreview(
        table={h: [*passive_rows] for h, passive_rows in passive_rows_by_host.items()},
        labels=host_labels,
        source_results={
            src.ident: result for (src, _sections), result in zip(parsed, summarizer(parsed))
        },
        kept_labels=kept_labels,
    )


def _check_preview_table_row(
    host_name: HostName,
    *,
    service: ConfiguredService,
    new_discovered_parameters: Mapping[str, object],
    new_service_labels: Mapping[str, str],
    check_plugins: Mapping[CheckPluginName, CheckerPlugin],
    check_source: _Transition | Literal["manual"],
    providers: Mapping[HostKey, Provider],
    found_on_nodes: Sequence[HostName],
) -> CheckPreviewEntry:
    check_plugin = check_plugins.get(service.check_plugin_name)
    ruleset_name = (
        str(check_plugin.ruleset_name) if check_plugin and check_plugin.ruleset_name else None
    )
    discovery_ruleset_name = (
        str(check_plugin.discovery_ruleset_name)
        if check_plugin and check_plugin.discovery_ruleset_name
        else None
    )

    result = (
        check_plugin.function(host_name, service, providers=providers).result
        if check_plugin is not None
        else SubmittableServiceCheckResult.check_not_implemented()
    )

    def make_output() -> str:
        return (
            result.output
            or f"WAITING - {check_source.split('_')[-1].title()} check, cannot be done offline"
        )

    return CheckPreviewEntry(
        check_source=check_source,
        check_plugin_name=str(service.check_plugin_name),
        ruleset_name=ruleset_name,
        discovery_ruleset_name=discovery_ruleset_name,
        item=service.item,
        old_discovered_parameters=service.discovered_parameters,
        new_discovered_parameters=new_discovered_parameters,
        effective_parameters=service.parameters.preview(timeperiod_active),
        description=service.description,
        state=result.state,
        output=make_output(),
        metrics=[],
        old_labels=service.discovered_labels,
        new_labels=new_service_labels,
        found_on_nodes=list(found_on_nodes),
    )
