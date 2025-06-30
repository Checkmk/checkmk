#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Performing the actual checks."""

import itertools
from abc import ABC, abstractmethod
from collections.abc import Callable, Container, Iterable, Mapping, Sequence
from typing import NamedTuple

from cmk.ccc.hostaddress import HostName
from cmk.ccc.resulttype import Result

import cmk.utils.paths
from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.log import console
from cmk.utils.regex import regex
from cmk.utils.sectionname import SectionMap, SectionName
from cmk.utils.servicename import ServiceName
from cmk.utils.structured_data import (
    InventoryStore,
)
from cmk.utils.timeperiod import check_timeperiod, TimeperiodName

from cmk.snmplib import SNMPRawData

from cmk.checkengine.checkresults import ActiveCheckResult, SubmittableServiceCheckResult
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.fetcher import HostKey, SourceInfo
from cmk.checkengine.inventory import (
    HWSWInventoryParameters,
    inventorize_status_data_of_real_host,
)
from cmk.checkengine.parser import group_by_host, ParserFunction
from cmk.checkengine.plugins import (
    AggregatedResult,
    CheckerPlugin,
    CheckPluginName,
    ConfiguredService,
    InventoryPlugin,
    InventoryPluginName,
)
from cmk.checkengine.sectionparser import (
    make_providers,
    Provider,
    SectionPlugin,
    store_piggybacked_sections,
)
from cmk.checkengine.sectionparserutils import check_parsing_errors
from cmk.checkengine.submitters import Submittee, Submitter
from cmk.checkengine.summarize import SummarizerFunction

__all__ = [
    "execute_checkmk_checks",
    "check_host_services",
    "check_plugins_missing_data",
    "ABCCheckingConfig",
]

type _Labels = Mapping[str, str]


class ABCCheckingConfig(ABC):
    @abstractmethod
    def __call__(
        self,
        host_name: HostName,
        item: str | None,
        service_labels: Mapping[str, str],
        ruleset_name: str,
    ) -> Sequence[Mapping[str, object]]: ...


def execute_checkmk_checks(
    *,
    hostname: HostName,
    fetched: Iterable[
        tuple[
            SourceInfo,
            Result[AgentRawData | SNMPRawData, Exception],
        ]
    ],
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    section_plugins: SectionMap[SectionPlugin],
    check_plugins: Mapping[CheckPluginName, CheckerPlugin],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
    inventory_parameters: Callable[[HostName, InventoryPlugin], Mapping[str, object]],
    params: HWSWInventoryParameters,
    services: Sequence[ConfiguredService],
    get_check_period: Callable[[ServiceName, _Labels], TimeperiodName | None],
    run_plugin_names: Container[CheckPluginName],
    submitter: Submitter,
    exit_spec: ExitSpec,
    section_error_handling: Callable[[SectionName, Sequence[object]], str],
) -> Sequence[ActiveCheckResult]:
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
    service_results = list(
        check_host_services(
            hostname,
            providers=providers,
            services=services,
            check_plugins=check_plugins,
            run_plugin_names=run_plugin_names,
            get_check_period=get_check_period,
        )
    )
    submitter.submit(
        Submittee(s.service.description, s.result, s.cache_info) for s in service_results
    )

    if run_plugin_names is EVERYTHING:
        _do_inventory_actions_during_checking_for(
            hostname,
            inventory_parameters=inventory_parameters,
            inventory_plugins=inventory_plugins,
            params=params,
            providers=providers,
        )
    timed_results = [
        *summarizer(host_sections),
        *check_parsing_errors(
            itertools.chain.from_iterable(
                resolver.parsing_errors for resolver in providers.values()
            )
        ),
        *check_plugins_missing_data(service_results, exit_spec),
    ]

    return timed_results


def _do_inventory_actions_during_checking_for(
    host_name: HostName,
    *,
    inventory_parameters: Callable[[HostName, InventoryPlugin], Mapping[str, object]],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
    params: HWSWInventoryParameters,
    providers: Mapping[HostKey, Provider],
) -> None:
    inv_store = InventoryStore(cmk.utils.paths.omd_root)

    if not params.status_data_inventory:
        # includes cluster case
        inv_store.remove_status_data_tree(host_name=host_name)
        return  # nothing to do here

    status_data_tree = inventorize_status_data_of_real_host(
        host_name,
        inventory_parameters=inventory_parameters,
        providers=providers,
        inventory_plugins=inventory_plugins,
        run_plugin_names=EVERYTHING,
    )

    if status_data_tree:
        inv_store.save_status_data_tree(host_name=host_name, tree=status_data_tree)


class PluginState(NamedTuple):
    state: int
    name: CheckPluginName


def check_plugins_missing_data(
    service_results: Sequence[AggregatedResult],
    exit_spec: ExitSpec,
) -> Iterable[ActiveCheckResult]:
    """Compute a state for the fact that plugins did not get any data"""

    # NOTE:
    # The keys used here are 'missing_sections' and 'specific_missing_sections'.
    # They are from a time where the distinction between section and plug-in was unclear.
    # They are kept for compatibility.
    missing_status = exit_spec.get("missing_sections", 1)
    specific_plugins_missing_data_spec = exit_spec.get("specific_missing_sections", [])

    if all(r.data_received for r in service_results):
        return

    if not any(r.data_received for r in service_results):
        yield ActiveCheckResult(
            state=missing_status,
            summary="Missing monitoring data for all plugins",
        )
        return

    plugins_missing_data = {
        r.service.check_plugin_name for r in service_results if not r.data_received
    }

    yield ActiveCheckResult(state=0, summary="Missing monitoring data for plugins")

    for check_plugin_name in sorted(plugins_missing_data):
        for pattern, status in specific_plugins_missing_data_spec:
            reg = regex(pattern)
            if reg.match(str(check_plugin_name)):
                yield ActiveCheckResult(state=status, summary=str(check_plugin_name))
                break
        else:  # no break
            yield ActiveCheckResult(state=missing_status, summary=str(check_plugin_name))


def check_host_services(
    host_name: HostName,
    *,
    providers: Mapping[HostKey, Provider],
    services: Sequence[ConfiguredService],
    check_plugins: Mapping[CheckPluginName, CheckerPlugin],
    run_plugin_names: Container[CheckPluginName],
    get_check_period: Callable[[ServiceName, _Labels], TimeperiodName | None],
) -> Iterable[AggregatedResult]:
    """Compute service state results for all given services on node or cluster"""
    for service in (
        s
        for s in services
        if s.check_plugin_name in run_plugin_names
        and not service_outside_check_period(
            s.description, get_check_period(s.description, s.labels)
        )
    ):
        if service.check_plugin_name not in check_plugins:
            yield AggregatedResult(
                service=service,
                data_received=True,
                result=SubmittableServiceCheckResult.check_not_implemented(),
                cache_info=None,
            )
        else:
            plugin = check_plugins[service.check_plugin_name]
            yield plugin.function(host_name, service, providers=providers)


def service_outside_check_period(description: ServiceName, period: TimeperiodName | None) -> bool:
    if period is None:
        return False
    if check_timeperiod(period):
        console.debug(f"Service {description}: time period {period} is currently active.")
        return False
    console.verbose(f"Skipping service {description}: currently not in time period {period}.")
    return True
