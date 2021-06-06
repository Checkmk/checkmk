#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Performing the actual checks."""

import copy
from collections import defaultdict
from typing import (
    Any,
    Callable,
    Container,
    DefaultDict,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from six import ensure_str

import cmk.utils.debug
import cmk.utils.version as cmk_version
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.cpu_tracking import CPUTracker, Snapshot
from cmk.utils.exceptions import MKTimeout, OnError
from cmk.utils.log import console
from cmk.utils.regex import regex
from cmk.utils.type_defs import (
    CheckPluginName,
    EVERYTHING,
    ExitSpec,
    HostAddress,
    HostName,
    HostKey,
    MetricTuple,
    ServiceCheckResult,
    ServiceName,
    SourceType,
    state_markers,
)

from cmk.core_helpers.protocol import FetcherMessage, FetcherType
from cmk.core_helpers.type_defs import Mode, NO_SELECTION, SectionNameCollection

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_table as check_table
import cmk.base.config as config
import cmk.base.core
import cmk.base.crash_reporting
import cmk.base.agent_based.inventory as inventory
import cmk.base.item_state as item_state
import cmk.base.license_usage as license_usage
import cmk.base.plugin_contexts as plugin_contexts
import cmk.base.utils
from cmk.base.agent_based.data_provider import make_broker, ParsedSectionsBroker
from cmk.base.agent_based.utils import (
    check_sources,
    get_section_kwargs,
    get_section_cluster_kwargs,
    check_parsing_errors,
)
from cmk.base.api.agent_based import checking_classes
from cmk.base.api.agent_based.register.check_plugins_legacy import wrap_parameters
from cmk.base.api.agent_based import value_store
from cmk.base.api.agent_based.type_defs import Parameters
from cmk.base.check_utils import LegacyCheckParameters, Service

from . import _legacy_mode, _submit_to_core
from .utils import (
    AggregatedResult,
    CHECK_NOT_IMPLEMENTED,
    ITEM_NOT_FOUND,
    RECEIVED_NO_DATA,
)

#.
#   .--Checking------------------------------------------------------------.
#   |               ____ _               _    _                            |
#   |              / ___| |__   ___  ___| | _(_)_ __   __ _                |
#   |             | |   | '_ \ / _ \/ __| |/ / | '_ \ / _` |               |
#   |             | |___| | | |  __/ (__|   <| | | | | (_| |               |
#   |              \____|_| |_|\___|\___|_|\_\_|_| |_|\__, |               |
#   |                                                 |___/                |
#   +----------------------------------------------------------------------+
#   | Execute the Check_MK checks on hosts                                 |
#   '----------------------------------------------------------------------'


@cmk.base.agent_based.decorator.handle_check_mk_check_result("mk", "Check_MK")
def active_check_checking(
    hostname: HostName,
    ipaddress: Optional[HostAddress],
    *,
    # The following arguments *must* remain optional for Nagios and the `DiscoCheckExecutor`.
    #   See Also: `cmk.base.discovery.active_check_discovery()`
    # TODO: can we drop them now that we slit up 'commandline_checking'?
    fetcher_messages: Sequence[FetcherMessage] = (),
    run_plugin_names: Container[CheckPluginName] = EVERYTHING,
    selected_sections: SectionNameCollection = NO_SELECTION,
    dry_run: bool = False,
    show_perfdata: bool = False,
) -> ActiveCheckResult:
    return _execute_checkmk_checks(
        hostname=hostname,
        ipaddress=ipaddress,
        fetcher_messages=fetcher_messages,
        run_plugin_names=run_plugin_names,
        selected_sections=selected_sections,
        dry_run=dry_run,
        show_perfdata=show_perfdata,
    )


# TODO: see if we can/should drop the decorator. If so, make hostname a kwarg-only
@cmk.base.agent_based.decorator.handle_check_mk_check_result("mk", "Check_MK")
def commandline_checking(
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    *,
    run_plugin_names: Container[CheckPluginName],
    selected_sections: SectionNameCollection,
    dry_run: bool,
    show_perfdata: bool,
) -> ActiveCheckResult:
    console.vverbose("Checkmk version %s\n", cmk_version.__version__)

    return _execute_checkmk_checks(
        hostname=host_name,
        ipaddress=ipaddress,
        fetcher_messages=(),
        run_plugin_names=run_plugin_names,
        selected_sections=selected_sections,
        dry_run=dry_run,
        show_perfdata=show_perfdata,
    )


def _execute_checkmk_checks(
    *,
    hostname: HostName,
    ipaddress: Optional[HostAddress],
    fetcher_messages: Sequence[FetcherMessage] = (),
    run_plugin_names: Container[CheckPluginName],
    selected_sections: SectionNameCollection,
    dry_run: bool,
    show_perfdata: bool,
) -> ActiveCheckResult:
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    exit_spec = host_config.exit_code_spec()

    mode = Mode.CHECKING if selected_sections is NO_SELECTION else Mode.FORCE_SECTIONS

    try:
        license_usage.try_history_update()

        # In case of keepalive we always have an ipaddress (can be 0.0.0.0 or :: when
        # address is unknown). When called as non keepalive ipaddress may be None or
        # is already an address (2nd argument)
        if ipaddress is None and not host_config.is_cluster:
            ipaddress = config.lookup_ip_address(host_config)

        services = config.resolve_service_dependencies(
            host_name=hostname,
            services=sorted(
                check_table.get_check_table(hostname).values(),
                key=lambda service: service.description,
            ),
        )

        with CPUTracker() as tracker:

            broker, source_results = make_broker(
                config_cache=config_cache,
                host_config=host_config,
                ip_address=ipaddress,
                mode=mode,
                selected_sections=selected_sections,
                file_cache_max_age=host_config.max_cachefile_age,
                fetcher_messages=fetcher_messages,
                force_snmp_cache_refresh=False,
                on_scan_error=OnError.RAISE,
            )

            num_success, plugins_missing_data = check_host_services(
                config_cache=config_cache,
                host_config=host_config,
                ipaddress=ipaddress,
                parsed_sections_broker=broker,
                services=services,
                run_plugin_names=run_plugin_names,
                dry_run=dry_run,
                show_perfdata=show_perfdata,
            )

            if run_plugin_names is EVERYTHING:
                inventory.do_inventory_actions_during_checking_for(
                    config_cache,
                    host_config,
                    ipaddress,
                    parsed_sections_broker=broker,
                )

            timed_results = ActiveCheckResult.from_subresults(
                *check_sources(
                    source_results=source_results,
                    mode=mode,
                    include_ok_results=True,
                ),
                check_parsing_errors(errors=broker.parsing_errors(),),
                *_check_plugins_missing_data(
                    plugins_missing_data,
                    exit_spec,
                    bool(num_success),
                ),
            )

        return ActiveCheckResult.from_subresults(
            timed_results,
            _timing_results(tracker, fetcher_messages),
        )

    finally:
        _submit_to_core.finalize()


def _timing_results(tracker: CPUTracker,
                    fetcher_messages: Sequence[FetcherMessage]) -> ActiveCheckResult:
    total_times = tracker.duration
    for msg in fetcher_messages:
        total_times += msg.stats.duration

    infotexts = ("execution time %.1f sec" % total_times.process.elapsed,)

    if not config.check_mk_perfdata_with_times:
        return ActiveCheckResult(0, infotexts, (),
                                 ("execution_time=%.3f" % total_times.process.elapsed,))

    perfdata = [
        "execution_time=%.3f" % total_times.process.elapsed,
        "user_time=%.3f" % total_times.process.user,
        "system_time=%.3f" % total_times.process.system,
        "children_user_time=%.3f" % total_times.process.children_user,
        "children_system_time=%.3f" % total_times.process.children_system,
    ]
    summary: DefaultDict[str, Snapshot] = defaultdict(Snapshot.null)
    for msg in fetcher_messages:
        if msg.fetcher_type in (
                FetcherType.PIGGYBACK,
                FetcherType.PROGRAM,
                FetcherType.SNMP,
                FetcherType.TCP,
        ):
            summary[{
                FetcherType.PIGGYBACK: "agent",
                FetcherType.PROGRAM: "ds",
                FetcherType.SNMP: "snmp",
                FetcherType.TCP: "agent",
            }[msg.fetcher_type]] += msg.stats.duration
    for phase, duration in summary.items():
        perfdata.append("cmk_time_%s=%.3f" % (phase, duration.idle))

    return ActiveCheckResult(0, infotexts, (), perfdata)


def _check_plugins_missing_data(
    plugins_missing_data: List[CheckPluginName],
    exit_spec: ExitSpec,
    some_success: bool,
) -> Iterable[ActiveCheckResult]:
    if not plugins_missing_data:
        return

    if not some_success:
        yield ActiveCheckResult(exit_spec.get("empty_output", 2), ("Got no information from host",),
                                (), ())
        return

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
        (f"Missing monitoring data for plugins: {plugin_list}{state_markers[missing_status]}",),
        (),
        (),
    )

    yield from (ActiveCheckResult(status, f"{plugin}{state_markers[status]}", (), ())
                for plugin, status in sorted(specific_plugins))


def check_host_services(
    *,
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    services: Sequence[Service],
    run_plugin_names: Container[CheckPluginName],
    dry_run: bool,
    show_perfdata: bool,
) -> Tuple[int, List[CheckPluginName]]:
    """Compute service state results for all given services on node or cluster

     * Loops over all services,
     * calls the check
     * examines the result and sends it to the core (unless `dry_run` is True).
    """
    num_success = 0
    plugins_missing_data: Set[CheckPluginName] = set()

    with plugin_contexts.current_host(host_config.hostname):
        with value_store.load_host_value_store(host_config.hostname,
                                               store_changes=not dry_run) as value_store_manager:
            for service in _filter_services_to_check(
                    services=services,
                    run_plugin_names=run_plugin_names,
                    config_cache=config_cache,
                    host_name=host_config.hostname,
            ):
                success = _execute_check(
                    parsed_sections_broker,
                    host_config,
                    ipaddress,
                    service,
                    dry_run=dry_run,
                    show_perfdata=show_perfdata,
                    value_store_manager=value_store_manager,
                )
                if success:
                    num_success += 1
                else:
                    plugins_missing_data.add(service.check_plugin_name)

    return num_success, sorted(plugins_missing_data)


def _filter_services_to_check(
    *,
    services: Sequence[Service],
    run_plugin_names: Container[CheckPluginName],
    config_cache: config.ConfigCache,
    host_name: HostName,
) -> List[Service]:
    """Filter list of services to check"""
    if run_plugin_names is EVERYTHING:
        return [
            service for service in services
            if not service_outside_check_period(config_cache, host_name, service.description)
        ]

    # If check types are specified (e.g. via command line), drop all others
    return [
        service for service in services if service.check_plugin_name in run_plugin_names and
        not service_outside_check_period(config_cache, host_name, service.description)
    ]


def service_outside_check_period(config_cache: config.ConfigCache, hostname: HostName,
                                 description: ServiceName) -> bool:
    period = config_cache.check_period_of_service(hostname, description)
    if period is None:
        return False

    if cmk.base.core.check_timeperiod(period):
        console.vverbose("Service %s: timeperiod %s is currently active.\n",
                         ensure_str(description), period)
        return False

    console.verbose("Skipping service %s: currently not in timeperiod %s.\n",
                    ensure_str(description), period)
    return True


def _execute_check(
    parsed_sections_broker: ParsedSectionsBroker,
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    service: Service,
    *,
    dry_run: bool,
    show_perfdata: bool,
    value_store_manager: value_store.ValueStoreManager,
) -> bool:

    plugin = agent_based_register.get_check_plugin(service.check_plugin_name)

    # check if we must use legacy mode. remove this block entirely one day
    if (plugin is not None and host_config.is_cluster and
            plugin.cluster_check_function.__name__ == "cluster_legacy_mode_from_hell"):
        submittable = _legacy_mode.get_aggregated_result(
            parsed_sections_broker,
            host_config.hostname,
            ipaddress,
            service,
            used_params=(  #
                time_resolved_check_parameters(service.parameters)  #
                if isinstance(service.parameters, cmk.base.config.TimespecificParamList) else
                service.parameters),
            value_store_manager=value_store_manager,
        )
    else:  # This is the new, shiny, 'normal' case.
        submittable = get_aggregated_result(
            parsed_sections_broker,
            host_config,
            ipaddress,
            service,
            plugin,
            lambda: _final_read_only_check_parameters(service.parameters),
            value_store_manager=value_store_manager,
        )

    if submittable.submit:
        _submit_to_core.check_result(
            host_name=host_config.hostname,
            service_name=service.description,
            result=submittable.result,
            cache_info=submittable.cache_info,
            dry_run=dry_run,
            show_perfdata=show_perfdata,
        )
    else:
        console.verbose(f"{service.description:20} PEND - {submittable.result[1]}\n")

    return submittable.data_received


def get_aggregated_result(
    parsed_sections_broker: ParsedSectionsBroker,
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    service: Service,
    plugin: Optional[checking_classes.CheckPlugin],
    params_function: Callable[[], Parameters],
    *,
    value_store_manager: value_store.ValueStoreManager,
) -> AggregatedResult:
    """Run the check function and aggregate the subresults

    This function is also called during discovery.
    """
    if plugin is None:
        return AggregatedResult(
            submit=True,
            data_received=True,
            result=CHECK_NOT_IMPLEMENTED,
            cache_info=None,
        )

    check_function = (plugin.cluster_check_function
                      if host_config.is_cluster else plugin.check_function)

    source_type = (SourceType.MANAGEMENT
                   if service.check_plugin_name.is_management_name() else SourceType.HOST)

    config_cache = config.get_config_cache()

    try:
        kwargs = get_section_cluster_kwargs(
            parsed_sections_broker,
            config_cache.get_clustered_service_node_keys(
                host_config.hostname,
                source_type,
                service.description,
            ) or [],
            plugin.sections,
        ) if host_config.is_cluster else get_section_kwargs(
            parsed_sections_broker,
            HostKey(host_config.hostname, ipaddress, source_type),
            plugin.sections,
        )

        if not kwargs and not service.check_plugin_name.is_management_name():
            # in 1.6 some plugins where discovered for management boards, but with
            # the regular host plugins name. In this case retry with the source type
            # forced to MANAGEMENT:
            kwargs = get_section_cluster_kwargs(
                parsed_sections_broker,
                config_cache.get_clustered_service_node_keys(
                    host_config.hostname,
                    SourceType.MANAGEMENT,
                    service.description,
                ) or [],
                plugin.sections,
            ) if host_config.is_cluster else get_section_kwargs(
                parsed_sections_broker,
                HostKey(host_config.hostname, ipaddress, SourceType.MANAGEMENT),
                plugin.sections,
            )

        if not kwargs:  # no data found
            return AggregatedResult(
                submit=False,
                data_received=False,
                result=RECEIVED_NO_DATA,
                cache_info=None,
            )

        kwargs = {
            **kwargs,
            **({} if service.item is None else {
                   "item": service.item
               }),
            **({} if plugin.check_default_parameters is None else {
                   "params": params_function()
               }),
        }

        with plugin_contexts.current_host(host_config.hostname), \
            plugin_contexts.current_service(service), \
            value_store_manager.namespace(service.id()):
            result = _aggregate_results(check_function(**kwargs))

    except (item_state.MKCounterWrapped, checking_classes.IgnoreResultsError) as e:
        msg = str(e) or "No service summary available"
        return AggregatedResult(
            submit=False,
            data_received=True,
            result=(0, msg, []),
            cache_info=None,
        )

    except MKTimeout:
        raise

    except Exception:
        if cmk.utils.debug.enabled():
            raise
        table = check_table.get_check_table(host_config.hostname, skip_autochecks=True)
        result = 3, cmk.base.crash_reporting.create_check_crash_dump(
            host_name=host_config.hostname,
            service_name=service.description,
            plugin_name=service.check_plugin_name,
            plugin_kwargs=globals().get("kwargs", {}),
            is_manual=service.id() in table,
        ), []

    return AggregatedResult(
        submit=True,
        data_received=True,
        result=result,
        cache_info=parsed_sections_broker.get_cache_info(plugin.sections),
    )


def _final_read_only_check_parameters(entries: LegacyCheckParameters) -> Parameters:
    raw_parameters = (time_resolved_check_parameters(entries) if isinstance(
        entries, cmk.base.config.TimespecificParamList) else entries)
    # TODO (mo): this needs cleaning up, once we've gotten rid of tuple parameters.
    # wrap_parameters is a no-op for dictionaries.
    # For auto-migrated plugins expecting tuples, they will be
    # unwrapped by a decorator of the original check_function.
    return Parameters(wrap_parameters(raw_parameters))


def time_resolved_check_parameters(
    entries: cmk.base.config.TimespecificParamList,) -> LegacyCheckParameters:

    # Check if first entry is not dict based or if its dict based
    # check if the tp_default_value is not a dict
    if not isinstance(entries[0], dict) or not isinstance(entries[0].get("tp_default_value", {}),
                                                          dict):
        # This rule is tuple based, means no dict-key merging
        if not isinstance(entries[0], dict):
            return entries[0]  # A tuple rule, simply return first match
        return _evaluate_timespecific_entry(
            entries[0])  # A timespecific rule, determine the correct tuple

    # This rule is dictionary based, evaluate all entries and merge matching keys
    timespecific_entries: Dict[str, Any] = {}
    for entry in entries[::-1]:
        if not isinstance(entry, dict):
            # Ignore (old) default parameters like
            #   'NAME_default_levels' = (80.0, 85.0)
            # A rule with a timespecifc parameter settings always has an
            # implicit default parameter set, even if no timeperiod matches.
            continue
        timespecific_entries.update(_evaluate_timespecific_entry(entry))

    return timespecific_entries


def _evaluate_timespecific_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    # Dictionary entries without timespecific settings
    if "tp_default_value" not in entry:
        return entry

    # Timespecific entry, start with default value and update with timespecific entry
    # Note: This combined_entry may be a dict or tuple, so the update mechanism must handle this correctly
    # A shallow copy is sufficient
    combined_entry = copy.copy(entry["tp_default_value"])
    for timeperiod_name, tp_entry in entry["tp_values"][::-1]:
        try:
            tp_active = cmk.base.core.timeperiod_active(timeperiod_name)
        except Exception:
            # Connection error
            if cmk.utils.debug.enabled():
                raise
            break

        if not tp_active:
            continue

        # If multiple timeperiods are active, their settings are also merged
        # This follows the same logic than merging different rules
        if isinstance(combined_entry, dict):
            combined_entry.update(tp_entry)
        else:
            combined_entry = tp_entry

    return combined_entry


def _add_state_marker(
    result_str: str,
    state_marker: str,
) -> str:
    return result_str if state_marker in result_str else result_str + state_marker


def _aggregate_results(subresults: checking_classes.CheckResult) -> ServiceCheckResult:

    perfdata, results = _consume_and_dispatch_result_types(subresults)
    needs_marker = len(results) > 1

    summaries: List[str] = []
    details: List[str] = []
    status = checking_classes.State.OK
    for result in results:
        status = checking_classes.State.worst(status, result.state)
        state_marker = state_markers[int(result.state)] if needs_marker else ""

        if result.summary:
            summaries.append(_add_state_marker(
                result.summary,
                state_marker,
            ))

        details.append(_add_state_marker(
            result.details,
            state_marker,
        ))

    # Empty list? Check returned nothing
    if not details:
        return ITEM_NOT_FOUND

    if not summaries:
        count = len(details)
        summaries.append("Everything looks OK - %d detail%s available" %
                         (count, "" if count == 1 else "s"))

    all_text = [", ".join(summaries)] + details
    return int(status), "\n".join(all_text).strip(), perfdata


def _consume_and_dispatch_result_types(
    subresults: checking_classes.CheckResult,
) -> Tuple[List[MetricTuple], List[checking_classes.Result]]:
    """Consume *all* check results, and *then* raise, if we encountered
    an IgnoreResults instance.
    """
    ignore_results: List[checking_classes.IgnoreResults] = []
    results: List[checking_classes.Result] = []
    perfdata: List[MetricTuple] = []

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
