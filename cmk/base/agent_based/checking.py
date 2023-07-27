#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Performing the actual checks."""

import itertools
from collections import defaultdict
from collections.abc import Callable, Container, Iterable, Mapping, Sequence
from contextlib import suppress
from typing import DefaultDict, NamedTuple

import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.check_utils import wrap_parameters
from cmk.utils.cpu_tracking import CPUTracker, Snapshot
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.exceptions import MKTimeout
from cmk.utils.hostaddress import HostName
from cmk.utils.log import console
from cmk.utils.regex import regex
from cmk.utils.resulttype import Result
from cmk.utils.sectionname import SectionMap
from cmk.utils.servicename import ServiceName
from cmk.utils.structured_data import TreeStore
from cmk.utils.timeperiod import check_timeperiod, timeperiod_active, TimeperiodName

from cmk.snmplib import SNMPRawData

from cmk.fetchers import FetcherType

from cmk.checkengine import crash_reporting
from cmk.checkengine.check_table import ConfiguredService
from cmk.checkengine.checking import CheckPlugin, CheckPluginName
from cmk.checkengine.checkresults import (
    ActiveCheckResult,
    MetricTuple,
    ServiceCheckResult,
    state_markers,
)
from cmk.checkengine.error_handling import ExitSpec
from cmk.checkengine.fetcher import HostKey, SourceInfo, SourceType
from cmk.checkengine.inventory import (
    HWSWInventoryParameters,
    inventorize_status_data_of_real_host,
    InventoryPlugin,
    InventoryPluginName,
)
from cmk.checkengine.legacy import LegacyCheckParameters
from cmk.checkengine.parameters import Parameters, TimespecificParameters
from cmk.checkengine.parser import group_by_host, ParserFunction
from cmk.checkengine.sectionparser import (
    make_providers,
    ParsedSectionName,
    Provider,
    ResolvedResult,
    SectionPlugin,
    store_piggybacked_sections,
)
from cmk.checkengine.sectionparserutils import (
    check_parsing_errors,
    get_cache_info,
    get_section_cluster_kwargs,
    get_section_kwargs,
)
from cmk.checkengine.submitters import Submittee, Submitter
from cmk.checkengine.summarize import SummarizerFunction

from cmk.base.agent_based import plugin_contexts
from cmk.base.api.agent_based import cluster_mode, value_store
from cmk.base.api.agent_based.checking_classes import consume_check_results, IgnoreResultsError
from cmk.base.api.agent_based.checking_classes import Result as CheckFunctionResult
from cmk.base.api.agent_based.checking_classes import State
from cmk.base.api.agent_based.value_store import ValueStoreManager
from cmk.base.config import ConfigCache

__all__ = [
    "execute_checkmk_checks",
    "check_host_services",
    "get_aggregated_result",
]


class _AggregatedResult(NamedTuple):
    service: ConfiguredService
    submit: bool
    data_received: bool
    result: ServiceCheckResult
    cache_info: tuple[int, int] | None


def execute_checkmk_checks(
    *,
    hostname: HostName,
    is_cluster: bool,
    cluster_nodes: Sequence[HostName],
    config_cache: ConfigCache,
    fetched: Sequence[
        tuple[
            SourceInfo,
            Result[AgentRawData | SNMPRawData, Exception],
            Snapshot,
        ]
    ],
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    section_plugins: SectionMap[SectionPlugin],
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
    inventory_parameters: Callable[[HostName, InventoryPlugin], Mapping[str, object]],
    params: HWSWInventoryParameters,
    services: Sequence[ConfiguredService],
    get_effective_host: Callable[[HostName, ServiceName], HostName],
    get_check_period: Callable[[ServiceName], TimeperiodName | None],
    run_plugin_names: Container[CheckPluginName],
    perfdata_with_times: bool,
    submitter: Submitter,
    exit_spec: ExitSpec,
) -> ActiveCheckResult:
    host_sections = parser((f[0], f[1]) for f in fetched)
    host_sections_by_host = group_by_host(
        (HostKey(s.hostname, s.source_type), r.ok) for s, r in host_sections if r.is_ok()
    )
    store_piggybacked_sections(host_sections_by_host)
    providers = make_providers(host_sections_by_host, section_plugins)
    with CPUTracker() as tracker:
        with plugin_contexts.current_host(hostname):
            with value_store.load_host_value_store(
                hostname, store_changes=not submitter.dry_run
            ) as value_store_manager:
                service_results = check_host_services(
                    hostname,
                    is_cluster=is_cluster,
                    cluster_nodes=cluster_nodes,
                    config_cache=config_cache,
                    providers=providers,
                    services=services,
                    check_plugins=check_plugins,
                    run_plugin_names=run_plugin_names,
                    get_effective_host=get_effective_host,
                    get_check_period=get_check_period,
                    submitter=submitter,
                    value_store_manager=value_store_manager,
                    rtc_package=None,
                )
        if run_plugin_names is EVERYTHING:
            _do_inventory_actions_during_checking_for(
                hostname,
                inventory_parameters=inventory_parameters,
                inventory_plugins=inventory_plugins,
                params=params,
                providers=providers,
            )
        timed_results = itertools.chain(
            summarizer(host_sections),
            check_parsing_errors(
                itertools.chain.from_iterable(
                    resolver.parsing_errors for resolver in providers.values()
                )
            ),
            _check_plugins_missing_data(
                service_results,
                exit_spec,
            ),
        )
    return ActiveCheckResult.from_subresults(
        *timed_results,
        _timing_results(
            tracker.duration,
            tuple((f[0], f[2]) for f in fetched),
            perfdata_with_times=perfdata_with_times,
        ),
    )


def _do_inventory_actions_during_checking_for(
    host_name: HostName,
    *,
    inventory_parameters: Callable[[HostName, InventoryPlugin], Mapping[str, object]],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
    params: HWSWInventoryParameters,
    providers: Mapping[HostKey, Provider],
) -> None:
    tree_store = TreeStore(cmk.utils.paths.status_data_dir)

    if not params.status_data_inventory:
        # includes cluster case
        tree_store.remove(host_name=host_name)
        return  # nothing to do here

    status_data_tree = inventorize_status_data_of_real_host(
        host_name,
        inventory_parameters=inventory_parameters,
        providers=providers,
        inventory_plugins=inventory_plugins,
        run_plugin_names=EVERYTHING,
    )

    if status_data_tree:
        tree_store.save(host_name=host_name, tree=status_data_tree)


def _timing_results(
    total_times: Snapshot,
    fetched: Sequence[tuple[SourceInfo, Snapshot]],
    *,
    perfdata_with_times: bool,
) -> ActiveCheckResult:
    for duration in (f[1] for f in fetched):
        total_times += duration

    infotext = "execution time %.1f sec" % total_times.process.elapsed
    if not perfdata_with_times:
        return ActiveCheckResult(
            0, infotext, (), ("execution_time=%.3f" % total_times.process.elapsed,)
        )
    perfdata = [
        "execution_time=%.3f" % total_times.process.elapsed,
        "user_time=%.3f" % total_times.process.user,
        "system_time=%.3f" % total_times.process.system,
        "children_user_time=%.3f" % total_times.process.children_user,
        "children_system_time=%.3f" % total_times.process.children_system,
    ]

    summary: DefaultDict[str, Snapshot] = defaultdict(Snapshot.null)
    for source, duration in fetched:
        with suppress(KeyError):
            summary[
                {
                    FetcherType.PIGGYBACK: "agent",
                    FetcherType.PROGRAM: "ds",
                    FetcherType.SPECIAL_AGENT: "ds",
                    FetcherType.SNMP: "snmp",
                    FetcherType.TCP: "agent",
                }[source.fetcher_type]
            ] += duration

    for phase, duration in summary.items():
        perfdata.append(f"cmk_time_{phase}={duration.idle:.3f}")

    return ActiveCheckResult(0, infotext, (), perfdata)


def _check_plugins_missing_data(
    service_results: Sequence[_AggregatedResult],
    exit_spec: ExitSpec,
) -> Iterable[ActiveCheckResult]:
    """Compute a state for the fact that plugins did not get any data"""

    # NOTE:
    # The keys used here are 'missing_sections' and 'specific_missing_sections'.
    # They are from a time where the distinction between section and plugin was unclear.
    # They are kept for compatibility.
    missing_status = exit_spec.get("missing_sections", 1)
    specific_plugins_missing_data_spec = exit_spec.get("specific_missing_sections", [])

    if all(r.data_received for r in service_results):
        return

    if not any(r.data_received for r in service_results):
        yield ActiveCheckResult(
            missing_status,
            "Missing monitoring data for all plugins",
        )
        return

    plugins_missing_data = {
        r.service.check_plugin_name for r in service_results if not r.data_received
    }

    specific_plugins, generic_plugins = set(), set()
    for check_plugin_name in plugins_missing_data:
        for pattern, status in specific_plugins_missing_data_spec:
            reg = regex(pattern)
            if reg.match(str(check_plugin_name)):
                specific_plugins.add((check_plugin_name, status))
                break
        else:  # no break
            generic_plugins.add(str(check_plugin_name))

    plugin_list = ", ".join(sorted(generic_plugins))
    yield ActiveCheckResult(
        missing_status,
        f"Missing monitoring data for plugins: {plugin_list}",
    )
    yield from (
        ActiveCheckResult(status, str(plugin)) for plugin, status in sorted(specific_plugins)
    )


def check_host_services(
    host_name: HostName,
    *,
    is_cluster: bool,
    cluster_nodes: Sequence[HostName],
    config_cache: ConfigCache,
    providers: Mapping[HostKey, Provider],
    services: Sequence[ConfiguredService],
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
    run_plugin_names: Container[CheckPluginName],
    get_effective_host: Callable[[HostName, ServiceName], HostName],
    get_check_period: Callable[[ServiceName], TimeperiodName | None],
    submitter: Submitter,
    rtc_package: AgentRawData | None,
    value_store_manager: ValueStoreManager,
) -> Sequence[_AggregatedResult]:
    """Compute service state results for all given services on node or cluster

    * Loops over all services,
    * calls the check
    * examines the result and sends it to the core (unless `dry_run` is True).
    """
    submittables: list[_AggregatedResult] = []
    for service in (
        s
        for s in services
        if s.check_plugin_name in run_plugin_names
        and not service_outside_check_period(s.description, get_check_period(s.description))
    ):
        if service.check_plugin_name not in check_plugins:
            submittable = _AggregatedResult(
                service=service,
                submit=True,
                data_received=True,
                result=ServiceCheckResult.check_not_implemented(),
                cache_info=None,
            )
        else:
            submittable = get_aggregated_result(
                host_name,
                is_cluster,
                cluster_nodes,
                config_cache,
                providers,
                service,
                check_plugins[service.check_plugin_name],
                value_store_manager=value_store_manager,
                rtc_package=rtc_package,
                get_effective_host=get_effective_host,
            )
        submittables.append(submittable)

    if submittables:
        submitter.submit(
            submittees=[
                Submittee(s.service.description, s.result, s.cache_info, pending=not s.submit)
                for s in submittables
            ],
        )

    return submittables


def service_outside_check_period(description: ServiceName, period: TimeperiodName | None) -> bool:
    if period is None:
        return False
    if check_timeperiod(period):
        console.vverbose("Service %s: time period %s is currently active.\n", description, period)
        return False
    console.verbose("Skipping service %s: currently not in time period %s.\n", description, period)
    return True


def _get_check_function(
    config_cache: ConfigCache,
    host_name: HostName,
    is_cluster: bool,
    plugin: CheckPlugin,
    service: ConfiguredService,
    value_store_manager: value_store.ValueStoreManager,
) -> Callable[..., Iterable[object]]:
    return (
        cluster_mode.get_cluster_check_function(
            *config_cache.get_clustered_service_configuration(host_name, service.description),
            plugin=plugin,
            service_id=service.id(),
            value_store_manager=value_store_manager,
        )
        if is_cluster
        else plugin.function
    )


def get_aggregated_result(
    host_name: HostName,
    is_cluster: bool,
    cluster_nodes: Sequence[HostName],
    config_cache: ConfigCache,
    providers: Mapping[HostKey, Provider],
    service: ConfiguredService,
    plugin: CheckPlugin,
    *,
    rtc_package: AgentRawData | None,
    value_store_manager: value_store.ValueStoreManager,
    get_effective_host: Callable[[HostName, ServiceName], HostName],
) -> _AggregatedResult:
    """Run the check function and aggregate the subresults

    This function is also called during discovery.
    """
    check_function = _get_check_function(
        config_cache,
        host_name,
        is_cluster=is_cluster,
        plugin=plugin,
        service=service,
        value_store_manager=value_store_manager,
    )

    section_kws, error_result = get_monitoring_data_kwargs(
        host_name,
        is_cluster,
        providers,
        service,
        plugin.sections,
        cluster_nodes=cluster_nodes,
        get_effective_host=get_effective_host,
    )
    if not section_kws:  # no data found
        return _AggregatedResult(
            service=service,
            submit=False,
            data_received=False,
            result=error_result,
            cache_info=None,
        )

    item_kw = {} if service.item is None else {"item": service.item}
    params_kw = (
        {}
        if plugin.default_parameters is None
        else {"params": _final_read_only_check_parameters(service.parameters)}
    )

    try:
        with plugin_contexts.current_service(
            service.check_plugin_name, service.description
        ), value_store_manager.namespace(service.id()):
            result = _aggregate_results(
                consume_check_results(
                    check_function(
                        **item_kw,
                        **params_kw,
                        **section_kws,
                    )
                )
            )

    except IgnoreResultsError as e:
        msg = str(e) or "No service summary available"
        return _AggregatedResult(
            service=service,
            submit=False,
            data_received=True,
            result=ServiceCheckResult(output=msg),
            cache_info=None,
        )
    except MKTimeout:
        raise
    except Exception:
        if cmk.utils.debug.enabled():
            raise
        result = ServiceCheckResult(
            3,
            crash_reporting.create_check_crash_dump(
                host_name,
                service.description,
                plugin_name=service.check_plugin_name,
                plugin_kwargs={**item_kw, **params_kw, **section_kws},
                is_cluster=is_cluster,
                is_enforced=service.is_enforced,
                snmp_backend=config_cache.get_snmp_backend(host_name),
                rtc_package=rtc_package,
            ),
        )

    def __iter(
        section_names: Iterable[ParsedSectionName], providers: Mapping[HostKey, Provider]
    ) -> Iterable[ResolvedResult]:
        for provider in providers.values():
            yield from (
                resolved
                for section_name in section_names
                if (resolved := provider.resolve(section_name)) is not None
            )

    return _AggregatedResult(
        service=service,
        submit=True,
        data_received=True,
        result=result,
        cache_info=get_cache_info(
            tuple(
                cache_info
                for resolved in __iter(plugin.sections, providers)
                if (cache_info := resolved.cache_info) is not None
            )
        ),
    )


def _get_clustered_service_node_keys(
    cluster_name: HostName,
    source_type: SourceType,
    service_descr: ServiceName,
    *,
    cluster_nodes: Sequence[HostName],
    get_effective_host: Callable[[HostName, ServiceName], HostName],
) -> Sequence[HostKey]:
    """Returns the node keys if a service is clustered, otherwise an empty sequence"""
    used_nodes = (
        [nn for nn in cluster_nodes if cluster_name == get_effective_host(nn, service_descr)]
        or cluster_nodes  # IMHO: this can never happen, but if it does, using nodes is wrong.
        or ()
    )

    return [HostKey(nodename, source_type) for nodename in used_nodes]


def get_monitoring_data_kwargs(
    host_name: HostName,
    is_cluster: bool,
    providers: Mapping[HostKey, Provider],
    service: ConfiguredService,
    sections: Sequence[ParsedSectionName],
    source_type: SourceType | None = None,
    *,
    cluster_nodes: Sequence[HostName],
    get_effective_host: Callable[[HostName, ServiceName], HostName],
) -> tuple[Mapping[str, object], ServiceCheckResult]:
    # Mapping[str, object] stands for either
    #  * Mapping[HostName, Mapping[str, ParsedSectionContent | None]] for clusters, or
    #  * Mapping[str, ParsedSectionContent | None] otherwise.
    if source_type is None:
        source_type = (
            SourceType.MANAGEMENT
            if service.check_plugin_name.is_management_name()
            else SourceType.HOST
        )

    if is_cluster:
        nodes = _get_clustered_service_node_keys(
            host_name,
            source_type,
            service.description,
            cluster_nodes=cluster_nodes,
            get_effective_host=get_effective_host,
        )
        return (
            get_section_cluster_kwargs(
                providers,
                nodes,
                sections,
            ),
            ServiceCheckResult.cluster_received_no_data([nk.hostname for nk in nodes]),
        )

    return (
        get_section_kwargs(
            providers,
            HostKey(host_name, source_type),
            sections,
        ),
        ServiceCheckResult.received_no_data(),
    )


def _final_read_only_check_parameters(
    entries: TimespecificParameters | LegacyCheckParameters,
) -> Parameters:
    raw_parameters = (
        entries.evaluate(timeperiod_active)
        if isinstance(entries, TimespecificParameters)
        else entries
    )

    # TODO (mo): this needs cleaning up, once we've gotten rid of tuple parameters.
    # wrap_parameters is a no-op for dictionaries.
    # For auto-migrated plugins expecting tuples, they will be
    # unwrapped by a decorator of the original check_function.
    return Parameters(wrap_parameters(raw_parameters))


def _add_state_marker(
    result_str: str,
    state_marker: str,
) -> str:
    return result_str if state_marker in result_str else result_str + state_marker


def _aggregate_results(
    subresults: tuple[Sequence[MetricTuple], Sequence[CheckFunctionResult]]
) -> ServiceCheckResult:
    # This is more impedance matching.  The CheckFunction should
    # probably just return a CheckResult.
    perfdata, results = subresults
    needs_marker = len(results) > 1
    summaries: list[str] = []
    details: list[str] = []
    status = State.OK
    for result in results:
        status = State.worst(status, result.state)
        state_marker = state_markers[int(result.state)] if needs_marker else ""
        if result.summary:
            summaries.append(
                _add_state_marker(
                    result.summary,
                    state_marker,
                )
            )
        details.append(
            _add_state_marker(
                result.details,
                state_marker,
            )
        )

    # Empty list? Check returned nothing
    if not details:
        return ServiceCheckResult.item_not_found()

    if not summaries:
        count = len(details)
        summaries.append(
            "Everything looks OK - %d detail%s available" % (count, "" if count == 1 else "s")
        )
    all_text = [", ".join(summaries)] + details
    return ServiceCheckResult(int(status), "\n".join(all_text).strip(), perfdata)
