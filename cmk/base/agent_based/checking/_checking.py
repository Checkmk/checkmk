#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Performing the actual checks."""

import itertools
import logging
from collections import defaultdict
from collections.abc import Container, Iterable, Mapping, Sequence
from contextlib import suppress
from typing import Callable, DefaultDict, NamedTuple

import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.cpu_tracking import CPUTracker, Snapshot
from cmk.utils.exceptions import MKTimeout
from cmk.utils.log import console
from cmk.utils.parameters import TimespecificParameters
from cmk.utils.regex import regex
from cmk.utils.structured_data import TreeStore
from cmk.utils.type_defs import (
    AgentRawData,
    CheckPluginName,
    EVERYTHING,
    ExitSpec,
    HostName,
    MetricTuple,
    ParsedSectionName,
    RuleSetName,
    ServiceName,
    state_markers,
    TimeperiodName,
)
from cmk.utils.type_defs.result import Result

from cmk.snmplib.type_defs import SNMPRawData

from cmk.fetchers import FetcherType, SourceInfo, SourceType

from cmk.checkers import HostKey
from cmk.checkers.check_table import ConfiguredService, LegacyCheckParameters
from cmk.checkers.checkresults import ActiveCheckResult, ServiceCheckResult
from cmk.checkers.submitters import Submittee, Submitter
from cmk.checkers.type_defs import SectionNameCollection

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.core
import cmk.base.crash_reporting
import cmk.base.plugin_contexts as plugin_contexts
import cmk.base.utils
from cmk.base.agent_based.data_provider import (
    make_broker,
    parse_messages,
    ParsedSectionsBroker,
    store_piggybacked_sections,
)
from cmk.base.agent_based.inventory import inventorize_status_data_of_real_host
from cmk.base.agent_based.utils import (
    check_parsing_errors,
    get_section_cluster_kwargs,
    get_section_kwargs,
    summarize_host_sections,
)
from cmk.base.api.agent_based import checking_classes, value_store
from cmk.base.api.agent_based.register.check_plugins_legacy import wrap_parameters
from cmk.base.api.agent_based.type_defs import Parameters
from cmk.base.config import ConfigCache, HWSWInventoryParameters

from . import _cluster_modes

__all__ = ["execute_checkmk_checks", "check_host_services"]


class _AggregatedResult(NamedTuple):
    service: ConfiguredService
    submit: bool
    data_received: bool
    result: ServiceCheckResult
    cache_info: tuple[int, int] | None


def execute_checkmk_checks(
    *,
    hostname: HostName,
    config_cache: ConfigCache,
    fetched: Sequence[tuple[SourceInfo, Result[AgentRawData | SNMPRawData, Exception], Snapshot]],
    run_plugin_names: Container[CheckPluginName],
    keep_outdated: bool,
    selected_sections: SectionNameCollection,
    perfdata_with_times: bool,
    submitter: Submitter,
) -> ActiveCheckResult:
    exit_spec = config_cache.exit_code_spec(hostname)
    services = config_cache.configured_services(hostname)
    host_sections, source_results = parse_messages(
        config_cache,
        ((f[0], f[1]) for f in fetched),
        selected_sections=selected_sections,
        keep_outdated=keep_outdated,
        logger=logging.getLogger("cmk.base.checking"),
    )
    store_piggybacked_sections(host_sections)
    broker = make_broker(host_sections)
    with CPUTracker() as tracker:
        service_results = check_host_services(
            hostname,
            config_cache=config_cache,
            parsed_sections_broker=broker,
            services=services,
            run_plugin_names=run_plugin_names,
            submitter=submitter,
            rtc_package=None,
        )
        if run_plugin_names is EVERYTHING:
            _do_inventory_actions_during_checking_for(
                hostname,
                inventory_parameters=config_cache.inventory_parameters,
                params=config_cache.hwsw_inventory_parameters(hostname),
                parsed_sections_broker=broker,
            )
        timed_results = itertools.chain(
            *(
                summarize_host_sections(
                    host_sections,
                    source,
                    include_ok_results=True,
                    exit_spec=config_cache.exit_code_spec(source.hostname, source.ident),
                    time_settings=config_cache.get_piggybacked_hosts_time_settings(
                        piggybacked_hostname=source.hostname,
                    ),
                    is_piggyback=config_cache.is_piggyback_host(hostname),
                )
                for source, host_sections in source_results
            ),
            check_parsing_errors(
                errors=broker.parsing_errors(),
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
    inventory_parameters: Callable[[HostName, RuleSetName], dict[str, object]],
    params: HWSWInventoryParameters,
    parsed_sections_broker: ParsedSectionsBroker,
) -> None:
    tree_store = TreeStore(cmk.utils.paths.status_data_dir)

    if not params.status_data_inventory:
        # includes cluster case
        tree_store.remove(host_name=host_name)
        return  # nothing to do here

    status_data_tree = inventorize_status_data_of_real_host(
        host_name,
        inventory_parameters=inventory_parameters,
        parsed_sections_broker=parsed_sections_broker,
        run_plugin_names=EVERYTHING,
    )

    if status_data_tree and not status_data_tree.is_empty():
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

    if all(r.data_received for r in service_results):
        return

    if not any(r.data_received for r in service_results):
        yield ActiveCheckResult(exit_spec.get("empty_output", 2), "Got no information from host")
        return

    plugins_missing_data = {
        r.service.check_plugin_name for r in service_results if not r.data_received
    }

    # key is a legacy name, kept for compatibility.
    specific_plugins_missing_data_spec = exit_spec.get("specific_missing_sections", [])
    specific_plugins, generic_plugins = set(), set()
    for check_plugin_name in plugins_missing_data:
        for pattern, status in specific_plugins_missing_data_spec:
            reg = regex(pattern)
            if reg.match(str(check_plugin_name)):
                specific_plugins.add((check_plugin_name, status))
                break
        else:  # no break
            generic_plugins.add(str(check_plugin_name))

    # key is a legacy name, kept for compatibility.
    missing_status = exit_spec.get("missing_sections", 1)
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
    config_cache: ConfigCache,
    parsed_sections_broker: ParsedSectionsBroker,
    services: Sequence[ConfiguredService],
    run_plugin_names: Container[CheckPluginName],
    submitter: Submitter,
    rtc_package: AgentRawData | None,
) -> Sequence[_AggregatedResult]:
    """Compute service state results for all given services on node or cluster

    * Loops over all services,
    * calls the check
    * examines the result and sends it to the core (unless `dry_run` is True).
    """
    with plugin_contexts.current_host(host_name):
        with value_store.load_host_value_store(
            host_name, store_changes=not submitter.dry_run
        ) as value_store_manager:
            submittables = [
                get_aggregated_result(
                    host_name,
                    config_cache,
                    parsed_sections_broker,
                    service,
                    agent_based_register.get_check_plugin(service.check_plugin_name),
                    value_store_manager=value_store_manager,
                    rtc_package=rtc_package,
                )
                for service in _filter_services_to_check(
                    services=services,
                    run_plugin_names=run_plugin_names,
                    config_cache=config_cache,
                    host_name=host_name,
                )
            ]

    if submittables:
        submitter.submit(
            submittees=[
                Submittee(s.service.description, s.result, s.cache_info, pending=not s.submit)
                for s in submittables
            ],
        )

    return submittables


def _filter_services_to_check(
    *,
    services: Sequence[ConfiguredService],
    run_plugin_names: Container[CheckPluginName],
    config_cache: ConfigCache,
    host_name: HostName,
) -> Sequence[ConfiguredService]:
    """Filter list of services to check

    If check types are specified in `run_plugin_names` (e.g. via command line), drop all others
    """
    return [
        service
        for service in services
        if service.check_plugin_name in run_plugin_names
        and not service_outside_check_period(
            service.description,
            config_cache.check_period_of_service(host_name, service.description),
        )
    ]


def service_outside_check_period(description: ServiceName, period: TimeperiodName | None) -> bool:
    if period is None:
        return False
    if cmk.base.core.check_timeperiod(period):
        console.vverbose("Service %s: time period %s is currently active.\n", description, period)
        return False
    console.verbose("Skipping service %s: currently not in time period %s.\n", description, period)
    return True


def get_aggregated_result(
    host_name: HostName,
    config_cache: ConfigCache,
    parsed_sections_broker: ParsedSectionsBroker,
    service: ConfiguredService,
    plugin: checking_classes.CheckPlugin | None,
    *,
    rtc_package: AgentRawData | None,
    value_store_manager: value_store.ValueStoreManager,
) -> _AggregatedResult:
    """Run the check function and aggregate the subresults

    This function is also called during discovery.
    """
    if plugin is None:
        return _AggregatedResult(
            service=service,
            submit=True,
            data_received=True,
            result=ServiceCheckResult.check_not_implemented(),
            cache_info=None,
        )

    check_function = (
        _cluster_modes.get_cluster_check_function(
            *config_cache.get_clustered_service_configuration(host_name, service.description),
            plugin=plugin,
            service_id=service.id(),
            value_store_manager=value_store_manager,
        )
        if config_cache.is_cluster(host_name)
        else plugin.check_function
    )

    section_kws, error_result = _get_monitoring_data_kwargs(
        host_name, parsed_sections_broker, config_cache, service, plugin.sections
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
        if plugin.check_default_parameters is None
        else {"params": _final_read_only_check_parameters(service.parameters)}
    )

    try:
        with plugin_contexts.current_host(host_name), plugin_contexts.current_service(
            service.check_plugin_name, service.description
        ), value_store_manager.namespace(service.id()):
            result = _aggregate_results(
                check_function(
                    **item_kw,
                    **params_kw,
                    **section_kws,
                )
            )

    except checking_classes.IgnoreResultsError as e:
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
        table = config_cache.check_table(host_name, skip_autochecks=True)
        result = ServiceCheckResult(
            3,
            cmk.base.crash_reporting.create_check_crash_dump(
                host_name,
                service.description,
                plugin_name=service.check_plugin_name,
                plugin_kwargs={**item_kw, **params_kw, **section_kws},
                is_cluster=config_cache.is_cluster(host_name),
                is_enforced=service.id() in table,
                snmp_backend=config_cache.get_snmp_backend(host_name),
                rtc_package=rtc_package,
            ),
        )

    return _AggregatedResult(
        service=service,
        submit=True,
        data_received=True,
        result=result,
        cache_info=parsed_sections_broker.get_cache_info(plugin.sections),
    )


def _get_clustered_service_node_keys(
    config_cache: ConfigCache,
    host_name: HostName,
    source_type: SourceType,
    service_descr: ServiceName,
) -> Sequence[HostKey]:
    """Returns the node keys if a service is clustered, otherwise an empty sequence"""
    nodes = config_cache.nodes_of(host_name)
    used_nodes = (
        [
            nn
            for nn in (nodes or ())
            if host_name == config_cache.host_of_clustered_service(nn, service_descr)
        ]
        or nodes
        or ()
    )

    return [HostKey(nodename, source_type) for nodename in used_nodes]


def _get_monitoring_data_kwargs(
    host_name: HostName,
    parsed_sections_broker: ParsedSectionsBroker,
    config_cache: ConfigCache,
    service: ConfiguredService,
    sections: Sequence[ParsedSectionName],
    source_type: SourceType | None = None,
) -> tuple[Mapping[str, object], ServiceCheckResult]:
    if source_type is None:
        source_type = (
            SourceType.MANAGEMENT
            if service.check_plugin_name.is_management_name()
            else SourceType.HOST
        )

    if config_cache.is_cluster(host_name):
        nodes = _get_clustered_service_node_keys(
            config_cache,
            host_name,
            source_type,
            service.description,
        )
        return (
            get_section_cluster_kwargs(
                parsed_sections_broker,
                nodes,
                sections,
            ),
            ServiceCheckResult.cluster_received_no_data(nodes),
        )

    return (
        get_section_kwargs(
            parsed_sections_broker,
            HostKey(host_name, source_type),
            sections,
        ),
        ServiceCheckResult.received_no_data(),
    )


def _final_read_only_check_parameters(
    entries: TimespecificParameters | LegacyCheckParameters,
) -> Parameters:
    raw_parameters = (
        entries.evaluate(cmk.base.core.timeperiod_active)
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


def _aggregate_results(subresults: checking_classes.CheckResult) -> ServiceCheckResult:
    perfdata, results = _consume_and_dispatch_result_types(subresults)
    needs_marker = len(results) > 1
    summaries: list[str] = []
    details: list[str] = []
    status = checking_classes.State.OK
    for result in results:
        status = checking_classes.State.worst(status, result.state)
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


def _consume_and_dispatch_result_types(
    subresults: checking_classes.CheckResult,
) -> tuple[list[MetricTuple], list[checking_classes.Result]]:
    """Consume *all* check results, and *then* raise, if we encountered
    an IgnoreResults instance.
    """
    ignore_results: list[checking_classes.IgnoreResults] = []
    results: list[checking_classes.Result] = []
    perfdata: list[MetricTuple] = []
    for subr in subresults:
        if isinstance(subr, checking_classes.IgnoreResults):
            ignore_results.append(subr)
        elif isinstance(subr, checking_classes.Metric):
            perfdata.append((subr.name, subr.value) + subr.levels + subr.boundaries)
        else:
            results.append(subr)

    if ignore_results:
        raise checking_classes.IgnoreResultsError(str(ignore_results[-1]))

    return perfdata, results
