#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Performing the actual checks."""

import copy
import errno
import os
import signal
import time
from random import Random
from types import FrameType
from typing import (
    Any,
    AnyStr,
    Callable,
    cast,
    Dict,
    IO,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from six import ensure_binary, ensure_str

from cmk.utils.check_utils import is_management_name, maincheckify
import cmk.utils.debug
import cmk.utils.defines as defines
import cmk.utils.tty as tty
import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException, MKTimeout
from cmk.utils.log import console
from cmk.utils.regex import regex
from cmk.utils.type_defs import (
    CheckPluginName,
    HostAddress,
    HostName,
    InventoryPluginName,
    Metric,
    SectionName,
    ServiceAdditionalDetails,
    ServiceCheckResult,
    ServiceDetails,
    ServiceName,
    ServiceState,
    SourceType,
)

import cmk.base.check_api_utils as check_api_utils
import cmk.base.check_table as check_table
import cmk.base.config as config
import cmk.base.core
import cmk.base.cpu_tracking as cpu_tracking
import cmk.base.crash_reporting
import cmk.base.data_sources as data_sources
import cmk.base.decorator
import cmk.base.inventory as inventory
import cmk.base.ip_lookup as ip_lookup
import cmk.base.item_state as item_state
import cmk.base.utils
from cmk.base.api.agent_based import checking_types, value_store
from cmk.base.api.agent_based.register.check_plugins_legacy import (
    CLUSTER_LEGACY_MODE_FROM_HELL,
    wrap_parameters,
)
from cmk.base.check_utils import LegacyCheckParameters, Service, ServiceID
from cmk.base.check_api_utils import MGMT_ONLY as LEGACY_MGMT_ONLY
from cmk.base.data_sources.host_sections import HostKey, MultiHostSections

if not cmk_version.is_raw_edition():
    import cmk.base.cee.keepalive as keepalive  # type: ignore[import] # pylint: disable=no-name-in-module
    from cmk.fetchers.cee.snmp_backend import inline  # type: ignore[import] # pylint: disable=no-name-in-module, import-error, cmk-module-layer-violation
else:
    keepalive = None  # type: ignore[assignment]
    inline = None  # type: ignore[assignment]

# global variables used to cache temporary values that do not need
# to be reset after a configuration change.
# Filedescriptor to open nagios command pipe.
_nagios_command_pipe: Union[bool, IO[bytes], None] = None
_checkresult_file_fd = None
_checkresult_file_path = None

_submit_to_core = True
_show_perfdata = False

ServiceCheckResultWithOptionalDetails = Tuple[ServiceState, ServiceDetails, List[Metric]]
UncleanPerfValue = Union[None, str, float]

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

ITEM_NOT_FOUND: ServiceCheckResult = (3, "Item not found in monitoring data", [])

RECEIVED_NO_DATA: ServiceCheckResult = (3, "Check plugin received no monitoring data", [])

CHECK_NOT_IMPLEMENTED: ServiceCheckResult = (3, 'Check plugin not implemented', [])


@cmk.base.decorator.handle_check_mk_check_result("mk", "Check_MK")
def do_check(
    hostname: HostName,
    ipaddress: Optional[HostAddress],
    only_check_plugin_names: Optional[Set[CheckPluginName]] = None
) -> Tuple[int, List[ServiceDetails], List[ServiceAdditionalDetails], List[str]]:
    cpu_tracking.start("busy")
    console.verbose("Check_MK version %s\n", cmk_version.__version__)

    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    exit_spec = host_config.exit_code_spec()

    status: ServiceState = 0
    infotexts: List[ServiceDetails] = []
    long_infotexts: List[ServiceAdditionalDetails] = []
    perfdata: List[str] = []
    try:
        # In case of keepalive we always have an ipaddress (can be 0.0.0.0 or :: when
        # address is unknown). When called as non keepalive ipaddress may be None or
        # is already an address (2nd argument)
        if ipaddress is None and not host_config.is_cluster:
            ipaddress = ip_lookup.lookup_ip_address(hostname)

        item_state.load(hostname)

        services = _get_filtered_services(
            host_name=hostname,
            belongs_to_cluster=len(config_cache.clusters_of(hostname)) > 0,
            config_cache=config_cache,
            only_check_plugins=only_check_plugin_names,
        )

        # see which raw sections we may need
        selected_raw_sections = _get_relevant_raw_sections(services, host_config)

        sources = data_sources.make_sources(
            host_config,
            ipaddress,
            selected_raw_sections=selected_raw_sections,
        )
        mhs = data_sources.make_host_sections(
            host_config,
            ipaddress,
            sources=sources,
            max_cachefile_age=host_config.max_cachefile_age,
        )
        num_success, plugins_missing_data = _do_all_checks_on_host(
            host_config,
            ipaddress,
            multi_host_sections=mhs,
            selected_raw_sections=selected_raw_sections,
            services=services,
            only_check_plugins=only_check_plugin_names,
        )
        inventory.do_inventory_actions_during_checking_for(
            host_config,
            ipaddress,
            sources=sources,
            multi_host_sections=mhs,
            selected_raw_sections=selected_raw_sections,
        )

        if _submit_to_core:
            item_state.save(hostname)

        for source in sources:
            source_state, source_output, source_perfdata = source.get_summary_result_for_checking()
            if source_output != "":
                status = max(status, source_state)
                infotexts.append("[%s] %s" % (source.id(), source_output))
                perfdata.extend([_convert_perf_data(p) for p in source_perfdata])

        if plugins_missing_data:
            missing_data_status, missing_data_infotext = _check_plugins_missing_data(
                plugins_missing_data,
                exit_spec,
                bool(num_success),
            )
            status = max(status, missing_data_status)
            infotexts.append(missing_data_infotext)

        cpu_tracking.end()
        phase_times = cpu_tracking.get_times()
        total_times = phase_times["TOTAL"]
        run_time = total_times[4]

        infotexts.append("execution time %.1f sec" % run_time)
        if config.check_mk_perfdata_with_times:
            perfdata += [
                "execution_time=%.3f" % run_time,
                "user_time=%.3f" % total_times[0],
                "system_time=%.3f" % total_times[1],
                "children_user_time=%.3f" % total_times[2],
                "children_system_time=%.3f" % total_times[3],
            ]

            for phase, times in phase_times.items():
                if phase in ["agent", "snmp", "ds"]:
                    t = times[4] - sum(times[:4])  # real time - CPU time
                    perfdata.append("cmk_time_%s=%.3f" % (phase, t))
        else:
            perfdata.append("execution_time=%.3f" % run_time)

        return status, infotexts, long_infotexts, perfdata
    finally:
        if _checkresult_file_fd is not None:
            _close_checkresult_file()

        # "ipaddress is not None": At least when working with a cluster host it seems the ipaddress
        # may be None.  This needs to be understood in detail and cleaned up. As the InlineSNMP
        # stats feature is a very rarely used debugging feature, the analyzation and fix is
        # postponed now.
        if config.record_inline_snmp_stats \
           and ipaddress is not None \
           and host_config.snmp_config(ipaddress).is_inline_snmp_host:
            inline.snmp_stats_save()


def _get_relevant_raw_sections(services: List[Service], host_config: config.HostConfig):
    # see if we can remove this function, once inventory plugins have been migrated to
    # the new API. In particular, we schould be able to get rid of the imports.

    check_plugin_names: Iterable[CheckPluginName] = (
        CheckPluginName(maincheckify(s.check_plugin_name)) for s in services)

    if host_config.do_status_data_inventory:
        # This is called during checking, but the inventory plugins are not loaded yet
        import cmk.base.inventory_plugins as inventory_plugins  # pylint: disable=import-outside-toplevel
        from cmk.base.inventory import get_inventory_context  # pylint: disable=import-outside-toplevel
        from cmk.base.check_api import get_check_api_context  # pylint: disable=import-outside-toplevel
        inventory_plugins.load_plugins(get_check_api_context, get_inventory_context)
        inventory_plugin_names: Iterable[InventoryPluginName] = (InventoryPluginName(
            n.split('.')[0]) for n, _plugin in inventory_plugins.sorted_inventory_plugins())
    else:
        inventory_plugin_names = ()

    return config.get_relevant_raw_sections(
        check_plugin_names=check_plugin_names,
        inventory_plugin_names=inventory_plugin_names,
    )


def _check_plugins_missing_data(
    plugins_missing_data: List[CheckPluginName],
    exit_spec: config.ExitSpec,
    some_success: bool,
) -> Tuple[ServiceState, ServiceDetails]:
    if not some_success:
        return (cast(int, exit_spec.get("empty_output", 2)), "Got no information from host")

    specific_plugins_missing_data_spec = cast(
        List[config.ExitSpecSection],
        exit_spec.get("specific_missing_sections", []),
    )

    specific_plugins, generic_plugins = set(), set()
    for check_plugin_name in plugins_missing_data:
        for pattern, status in specific_plugins_missing_data_spec:
            reg = regex(pattern)
            if reg.match(str(check_plugin_name)):
                specific_plugins.add((check_plugin_name, status))
                break
        else:  # no break
            generic_plugins.add(str(check_plugin_name))

    generic_plugins_status = cast(int, exit_spec.get("missing_sections", 1))
    infotexts = [
        "Missing monitoring data for check plugins: %s%s" % (
            ", ".join(sorted(generic_plugins)),
            check_api_utils.state_markers[generic_plugins_status],
        ),
    ]

    for plugin, status in sorted(specific_plugins):
        infotexts.append("%s%s" % (plugin, check_api_utils.state_markers[status]))
        generic_plugins_status = max(generic_plugins_status, status)

    return generic_plugins_status, ", ".join(infotexts)


# Loops over all checks for ANY host (cluster, real host), gets the data, calls the check
# function that examines that data and sends the result to the Core.
def _do_all_checks_on_host(
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    multi_host_sections: MultiHostSections,
    *,
    selected_raw_sections: config.SelectedRawSections,
    services: List[Service],
    only_check_plugins: Optional[Set[CheckPluginName]] = None,
) -> Tuple[int, List[CheckPluginName]]:
    hostname: HostName = host_config.hostname
    num_success = 0
    plugins_missing_data: Set[CheckPluginName] = set()

    check_api_utils.set_hostname(hostname)
    for service in services:
        success = execute_check(multi_host_sections, host_config, ipaddress, service)
        if success:
            num_success += 1
        else:
            # TODO (mo): centralize maincheckify: CMK-4295
            plugins_missing_data.add(CheckPluginName(maincheckify(service.check_plugin_name)))

    return num_success, sorted(plugins_missing_data)


def _get_filtered_services(
    host_name: HostName,
    belongs_to_cluster: bool,
    config_cache: config.ConfigCache,
    only_check_plugins: Optional[Set[CheckPluginName]] = None,
) -> List[Service]:

    services = check_table.get_precompiled_check_table(
        host_name,
        remove_duplicates=True,
        filter_mode="include_clustered" if belongs_to_cluster else None,
    )

    # When check types are specified via command line, enforce them. Otherwise use the
    # list of checks defined by the check table.
    if only_check_plugins is None:
        only_check_plugins = {
            # TODO (mo): make service.check_plugin_name a CheckPluginName instance and thus
            # TODO (mo): centralize maincheckify: CMK-4295
            CheckPluginName(maincheckify(service.check_plugin_name)) for service in services
        }

    def _is_not_of_host(service):
        return host_name != config_cache.host_of_clustered_service(host_name, service.description)

    # Filter out check types which are not used on the node
    if belongs_to_cluster:
        removed_plugins = {
            plugin for plugin in only_check_plugins if all(
                _is_not_of_host(service) for service in services
                # TODO (mo): centralize maincheckify: CMK-4295
                if CheckPluginName(maincheckify(service.check_plugin_name)) == plugin)
        }
        only_check_plugins -= removed_plugins

    return [
        service for service in services if (
            # TODO (mo): centralize maincheckify: CMK-4295
            CheckPluginName(maincheckify(service.check_plugin_name)) in only_check_plugins and
            not (belongs_to_cluster and _is_not_of_host(service)) and
            not service_outside_check_period(config_cache, host_name, service.description))
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


def execute_check(multi_host_sections: MultiHostSections, host_config: config.HostConfig,
                  ipaddress: Optional[HostAddress], service: Service) -> bool:
    # TODO (mo): centralize maincheckify: CMK-4295
    plugin_name = CheckPluginName(maincheckify(service.check_plugin_name))
    plugin = config.get_registered_check_plugin(plugin_name)
    # check if we must use legacy mode. remove this block entirely one day
    if (plugin is not None and host_config.is_cluster and
            plugin.cluster_check_function.__name__ == CLUSTER_LEGACY_MODE_FROM_HELL):
        return _execute_check_legacy_mode(
            multi_host_sections,
            host_config.hostname,
            ipaddress,
            service,
        )

    submit, data_received, result = get_aggregated_result(
        multi_host_sections,
        host_config,
        ipaddress,
        service,
        plugin,
        lambda: determine_check_params(service.parameters),
    )

    if submit:
        _submit_check_result(
            host_config.hostname,
            service.description,
            result,
            multi_host_sections.get_cache_info(plugin.sections) if plugin else None,
        )
    elif data_received:
        console.verbose("%-20s PEND - %s\n", ensure_str(service.description), result[1])

    return data_received


def get_aggregated_result(
    multi_host_sections: MultiHostSections,
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    service: Service,
    plugin: Optional[checking_types.CheckPlugin],
    params_function: Callable[[], checking_types.Parameters],
) -> Tuple[bool, bool, ServiceCheckResult]:
    """Run the check function and aggregate the subresults

    This function is also called during discovery.

    Returns a triple:
       bool: should the result be submitted to the core
       bool: did we receive data for the plugin
       ServiceCheckResult: The aggregated result as returned by the plugin, or a fallback

    """
    if plugin is None:
        return False, True, CHECK_NOT_IMPLEMENTED

    check_function = (plugin.cluster_check_function
                      if host_config.is_cluster else plugin.check_function)

    source_type = (SourceType.MANAGEMENT
                   if is_management_name(service.check_plugin_name) else SourceType.HOST)

    kwargs = {}
    try:
        kwargs = multi_host_sections.get_section_cluster_kwargs(
            HostKey(host_config.hostname, None, source_type),
            plugin.sections,
            service.description,
        ) if host_config.is_cluster else multi_host_sections.get_section_kwargs(
            HostKey(host_config.hostname, ipaddress, source_type),
            plugin.sections,
        )

        if not kwargs and not is_management_name(service.check_plugin_name):
            # in 1.6 some plugins where discovered for management boards, but with
            # the regular host plugins name. In this case retry with the source type
            # forced to MANAGEMENT:
            kwargs = multi_host_sections.get_section_cluster_kwargs(
                HostKey(host_config.hostname, None, SourceType.MANAGEMENT),
                plugin.sections,
                service.description,
            ) if host_config.is_cluster else multi_host_sections.get_section_kwargs(
                HostKey(host_config.hostname, ipaddress, SourceType.MANAGEMENT),
                plugin.sections,
            )

        if not kwargs:  # no data found
            return False, False, RECEIVED_NO_DATA

        if service.item is not None:
            kwargs["item"] = service.item
        if plugin.check_ruleset_name:
            kwargs["params"] = params_function()

        with value_store.context(plugin.name, service.item):
            result = _aggregate_results(check_function(**kwargs))

    except (item_state.MKCounterWrapped, checking_types.IgnoreResultsError) as e:
        msg = str(e) or "No service summary available"
        return False, True, (0, msg, [])

    except MKTimeout:
        raise

    except Exception:
        if cmk.utils.debug.enabled():
            raise
        result = 3, cmk.base.crash_reporting.create_check_crash_dump(
            host_config.hostname,
            service.check_plugin_name,
            kwargs,
            is_manual_check(host_config.hostname, service.id()),
            service.description,
        ), []

    return True, True, result


def _execute_check_legacy_mode(multi_host_sections: MultiHostSections, hostname: HostName,
                               ipaddress: Optional[HostAddress], service: Service) -> bool:
    # This is weird, for the moment. Once service.check_plugin_name no longer *is*
    # the legacy name, this will make much more sense.
    legacy_check_plugin_name = service.check_plugin_name
    service_check_plugin_name = CheckPluginName(maincheckify(service.check_plugin_name))

    check_function = config.check_info[legacy_check_plugin_name].get("check_function")
    if check_function is None:
        _submit_check_result(hostname, service.description, CHECK_NOT_IMPLEMENTED, None)
        return True
    # Make a bit of context information globally available, so that functions
    # called by checks know this context
    check_api_utils.set_service(service_check_plugin_name, service.description)
    item_state.set_item_state_prefix(str(service_check_plugin_name), service.item)

    section_name = legacy_check_plugin_name.split('.')[0]

    section_content = None
    mgmt_board_info = config.get_management_board_precedence(section_name, config.check_info)
    try:
        section_content = multi_host_sections.get_section_content(
            HostKey(
                hostname,
                ipaddress,
                SourceType.MANAGEMENT if mgmt_board_info == LEGACY_MGMT_ONLY else SourceType.HOST,
            ),
            mgmt_board_info,
            section_name,
            for_discovery=False,
            service_description=service.description,
        )

        # TODO: Move this to a helper function
        if section_content is None:  # No data for this check type
            return False

        # Call the actual check function
        item_state.reset_wrapped_counters()

        used_params = legacy_determine_check_params(service.parameters)
        raw_result = check_function(service.item, used_params, section_content)
        result = sanitize_check_result(raw_result)
        item_state.raise_counter_wrap()

    except item_state.MKCounterWrapped as e:
        # handle check implementations that do not yet support the
        # handling of wrapped counters via exception on their own.
        # Do not submit any check result in that case:
        console.verbose("%-20s PEND - Cannot compute check result: %s\n",
                        ensure_str(service.description), e)
        # Don't submit to core - we're done.
        return True

    except MKTimeout:
        raise

    except Exception:
        if cmk.utils.debug.enabled():
            raise
        result = 3, cmk.base.crash_reporting.create_check_crash_dump(
            hostname,
            service.check_plugin_name,
            {
                "item": service.item,
                "params": used_params,
                "section_content": section_content
            },
            is_manual_check(hostname, service.id()),
            service.description,
        ), []

    _submit_check_result(
        hostname,
        service.description,
        result,
        _legacy_determine_cache_info(multi_host_sections, SectionName(section_name)),
    )
    return True


def _legacy_determine_cache_info(multi_host_sections: MultiHostSections,
                                 section_name: SectionName) -> Optional[Tuple[int, int]]:
    """Aggregate information about the age of the data in the agent sections

    This is in data_sources.g_agent_cache_info. For clusters we use the oldest
    of the timestamps, of course.
    """
    cached_ats: List[int] = []
    intervals: List[int] = []
    for host_sections in multi_host_sections.values():
        section_entries = host_sections.cache_info
        if section_name in section_entries:
            cached_at, cache_interval = section_entries[section_name]
            cached_ats.append(cached_at)
            intervals.append(cache_interval)

    return (min(cached_ats), max(intervals)) if cached_ats else None


def determine_check_params(entries: LegacyCheckParameters) -> checking_types.Parameters:
    # TODO (mo): obviously, we do not want to keep legacy_determine_check_params
    # around in the long run. This needs cleaning up, once we've gotten
    # rid of tuple parameters.
    params = legacy_determine_check_params(entries)
    # wrap_parameters is a no-op for dictionaries.
    # For auto-migrated plugins expecting tuples, they will be
    # unwrapped by a decorator of the original check_function.
    return checking_types.Parameters(wrap_parameters(params))


def legacy_determine_check_params(entries: LegacyCheckParameters) -> LegacyCheckParameters:
    if not isinstance(entries, cmk.base.config.TimespecificParamList):
        return entries

    # Check if first entry is not dict based or if its dict based
    # check if the tp_default_value is not a dict
    if not isinstance(entries[0], dict) or \
       not isinstance(entries[0].get("tp_default_value", {}), dict):
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


def is_manual_check(hostname: HostName, service_id: ServiceID) -> bool:
    return service_id in check_table.get_check_table(
        hostname,
        remove_duplicates=True,
        skip_autochecks=True,
    )


def _aggregate_results(
    subresults: Iterable[Union[checking_types.Metric, checking_types.Result,
                               checking_types.IgnoreResults]]
) -> ServiceCheckResult:
    perfdata: List[Metric] = []
    summaries: List[str] = []
    details: List[str] = []
    status = checking_types.state(0)

    for subr in list(subresults):  # consume *everything* here, before we may raise!
        if isinstance(subr, checking_types.IgnoreResults):
            raise checking_types.IgnoreResultsError(str(subr))
        if isinstance(subr, checking_types.Metric):
            perfdata.append((subr.name, subr.value) + subr.levels + subr.boundaries)
            continue

        status = checking_types.state.worst(status, subr.state)
        state_marker = check_api_utils.state_markers[int(subr.state)]

        if subr.summary:
            summaries.append(subr.summary + state_marker)

        details.append(subr.details + state_marker)

    # Empty list? Check returned nothing
    if not details:
        return ITEM_NOT_FOUND

    if not summaries:
        count = len(details)
        summaries.append("Everything looks OK - %d detail%s available" %
                         (count, "" if count == 1 else "s"))

    all_text = [", ".join(summaries)] + details
    return int(status), "\n".join(all_text).strip(), perfdata


def sanitize_check_result(
        result: Union[None, ServiceCheckResult, Tuple, Iterable]) -> ServiceCheckResult:
    if isinstance(result, tuple):
        return cast(ServiceCheckResult, _sanitize_tuple_check_result(result))

    if result is None:
        return ITEM_NOT_FOUND

    return _sanitize_yield_check_result(result)


# The check function may return an iterator (using yield) since 1.2.5i5.
# This function handles this case and converts them to tuple results
def _sanitize_yield_check_result(result: Iterable[Any]) -> ServiceCheckResult:
    subresults = list(result)

    # Empty list? Check returned nothing
    if not subresults:
        return ITEM_NOT_FOUND

    # Several sub results issued with multiple yields. Make that worst sub check
    # decide the total state, join the texts and performance data. Subresults with
    # an infotext of None are used for adding performance data.
    perfdata: List[Metric] = []
    infotexts: List[ServiceDetails] = []
    status: ServiceState = 0

    for subresult in subresults:
        st, text, perf = _sanitize_tuple_check_result(subresult, allow_missing_infotext=True)
        status = cmk.base.utils.worst_service_state(st, status)

        if text:
            infotexts.append(text + check_api_utils.state_markers[st])

        if perf is not None:
            perfdata += perf

    return status, ", ".join(infotexts), perfdata


# TODO: Cleanup return value: Factor "infotext: Optional[str]" case out and then make Tuple values
# more specific
def _sanitize_tuple_check_result(
        result: Tuple,
        allow_missing_infotext: bool = False) -> ServiceCheckResultWithOptionalDetails:
    if len(result) >= 3:
        state, infotext, perfdata = result[:3]
        _validate_perf_data_values(perfdata)
    else:
        state, infotext = result
        perfdata = []

    infotext = _sanitize_check_result_infotext(infotext, allow_missing_infotext)

    return state, infotext, perfdata


def _validate_perf_data_values(perfdata: Any) -> None:
    if not isinstance(perfdata, list):
        return
    for v in [value for entry in perfdata for value in entry[1:]]:
        if " " in str(v):
            # See Nagios performance data spec for detailed information
            raise MKGeneralException("Performance data values must not contain spaces")


def _sanitize_check_result_infotext(infotext: Optional[AnyStr],
                                    allow_missing_infotext: bool) -> Optional[ServiceDetails]:
    if infotext is None and not allow_missing_infotext:
        raise MKGeneralException("Invalid infotext from check: \"None\"")

    if isinstance(infotext, bytes):
        return infotext.decode('utf-8')

    return infotext


def _convert_perf_data(p: List[UncleanPerfValue]) -> str:
    # replace None with "" and fill up to 6 values
    normalized = (list(map(_convert_perf_value, p)) + ['', '', '', ''])[0:6]
    return "%s=%s;%s;%s;%s;%s" % tuple(normalized)


def _convert_perf_value(x: UncleanPerfValue) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, float):
        return ("%.6f" % x).rstrip("0").rstrip(".")

    return str(x)


#.
#   .--Submit to core------------------------------------------------------.
#   |  ____        _               _ _     _                               |
#   | / ___| _   _| |__  _ __ ___ (_) |_  | |_ ___     ___ ___  _ __ ___   |
#   | \___ \| | | | '_ \| '_ ` _ \| | __| | __/ _ \   / __/ _ \| '__/ _ \  |
#   |  ___) | |_| | |_) | | | | | | | |_  | || (_) | | (_| (_) | | |  __/  |
#   | |____/ \__,_|_.__/|_| |_| |_|_|\__|  \__\___/   \___\___/|_|  \___|  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Submit check results to the core. Care about different methods       |
#   | depending on the running core.                                       |
#   '----------------------------------------------------------------------'
# TODO: Put the core specific things to dedicated files


def _submit_check_result(host: HostName, servicedesc: ServiceDetails, result: ServiceCheckResult,
                         cache_info: Optional[Tuple[int, int]]) -> None:
    state, infotext, perfdata = result

    if not (infotext.startswith("OK -") or infotext.startswith("WARN -") or
            infotext.startswith("CRIT -") or infotext.startswith("UNKNOWN -")):
        infotext = defines.short_service_state_name(state) + " - " + infotext

    # make sure that plugin output does not contain a vertical bar. If that is the
    # case then replace it with a Uniocode "Light vertical bar"
    if isinstance(infotext, str):
        # regular check results are unicode...
        infotext = infotext.replace(u"|", u"\u2758")
    else:
        # ...crash dumps, and hard-coded outputs are regular strings
        infotext = infotext.replace("|", u"\u2758".encode("utf8"))

    # performance data - if any - is stored in the third part of the result
    perftexts = []
    perftext = ""

    if perfdata:
        # Check may append the name of the check command to the
        # list of perfdata. It is of type string. And it might be
        # needed by the graphing tool in order to choose the correct
        # template. Currently this is used only by mrpe.
        if len(perfdata) > 0 and isinstance(perfdata[-1], str):
            check_command = perfdata[-1]
            del perfdata[-1]
        else:
            check_command = None

        for p in perfdata:
            perftexts.append(_convert_perf_data(p))

        if perftexts != []:
            if check_command and config.perfdata_format == "pnp":
                perftexts.append("[%s]" % check_command)
            perftext = "|" + (" ".join(perftexts))

    if _submit_to_core:
        _do_submit_to_core(host, servicedesc, state, infotext + perftext, cache_info)

    _output_check_result(servicedesc, state, infotext, perftexts)


def _output_check_result(servicedesc: ServiceName, state: ServiceState, infotext: ServiceDetails,
                         perftexts: List[str]) -> None:
    if _show_perfdata:
        infotext_fmt = "%-56s"
        p = ' (%s)' % (" ".join(perftexts))
    else:
        p = ''
        infotext_fmt = "%s"

    console.verbose("%-20s %s%s" + infotext_fmt + "%s%s\n", ensure_str(servicedesc),
                    tty.bold, tty.states[state], ensure_str(infotext.split('\n')[0]), tty.normal,
                    ensure_str(p))


def _do_submit_to_core(
    host: HostName,
    service: ServiceName,
    state: ServiceState,
    output: ServiceDetails,
    cache_info: Optional[Tuple[int, int]],
) -> None:
    if _in_keepalive_mode():
        cached_at, cache_interval = cache_info or (None, None)
        # Regular case for the CMC - check helpers are running in keepalive mode
        keepalive.add_check_result(host, service, state, output, cached_at, cache_interval)

    elif config.check_submission == "pipe" or config.monitoring_core == "cmc":
        # In case of CMC this is used when running "cmk" manually
        _submit_via_command_pipe(host, service, state, output)

    elif config.check_submission == "file":
        _submit_via_check_result_file(host, service, state, output)

    else:
        raise MKGeneralException("Invalid setting %r for check_submission. "
                                 "Must be 'pipe' or 'file'" % config.check_submission)


def _submit_via_check_result_file(host: HostName, service: ServiceName, state: ServiceState,
                                  output: ServiceDetails) -> None:
    output = output.replace("\n", "\\n")
    _open_checkresult_file()
    if _checkresult_file_fd:
        now = time.time()
        os.write(
            _checkresult_file_fd,
            ensure_binary("""host_name=%s
service_description=%s
check_type=1
check_options=0
reschedule_check
latency=0.0
start_time=%.1f
finish_time=%.1f
return_code=%d
output=%s

""" % (ensure_str(host), ensure_str(service), now, now, state, ensure_str(output))))


def _open_checkresult_file() -> None:
    global _checkresult_file_fd
    global _checkresult_file_path
    if _checkresult_file_fd is None:
        try:
            _checkresult_file_fd, _checkresult_file_path = _create_nagios_check_result_file()
        except Exception as e:
            raise MKGeneralException("Cannot create check result file in %s: %s" %
                                     (cmk.utils.paths.check_result_path, e))


def _create_nagios_check_result_file() -> Tuple[int, str]:
    """Create some temporary file for storing the checkresults.
    Nagios expects a seven character long file starting with "c". Since Python3 we can not
    use tempfile.mkstemp anymore since it produces file names with 9 characters length.

    Logic is similar to tempfile.mkstemp, but simplified. No prefix/suffix/thread-safety
    """

    base_dir = cmk.utils.paths.check_result_path

    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW

    names = _get_candidate_names()
    for _seq in range(os.TMP_MAX):
        name = next(names)
        filepath = os.path.join(base_dir, "c" + name)
        try:
            fd = os.open(filepath, flags, 0o600)
        except FileExistsError:
            continue  # try again
        return (fd, os.path.abspath(filepath))

    raise FileExistsError(errno.EEXIST, "No usable temporary file name found")


_name_sequence: 'Optional[_RandomNameSequence]' = None


def _get_candidate_names() -> '_RandomNameSequence':
    global _name_sequence
    if _name_sequence is None:
        _name_sequence = _RandomNameSequence()
    return _name_sequence


class _RandomNameSequence:
    """An instance of _RandomNameSequence generates an endless
    sequence of unpredictable strings which can safely be incorporated
    into file names.  Each string is eight characters long.  Multiple
    threads can safely use the same instance at the same time.

    _RandomNameSequence is an iterator."""

    characters = "abcdefghijklmnopqrstuvwxyz0123456789_"

    @property
    def rng(self) -> Random:
        cur_pid = os.getpid()
        if cur_pid != getattr(self, '_rng_pid', None):
            self._rng = Random()
            self._rng_pid = cur_pid
        return self._rng

    def __iter__(self) -> '_RandomNameSequence':
        return self

    def __next__(self) -> str:
        c = self.characters
        choose = self.rng.choice
        letters = [choose(c) for dummy in range(6)]
        return ''.join(letters)


def _close_checkresult_file() -> None:
    global _checkresult_file_fd
    if _checkresult_file_fd is not None and _checkresult_file_path is not None:
        os.close(_checkresult_file_fd)
        _checkresult_file_fd = None

        with open(_checkresult_file_path + ".ok", "w"):
            pass


def _submit_via_command_pipe(host: HostName, service: ServiceName, state: ServiceState,
                             output: ServiceDetails) -> None:
    output = output.replace("\n", "\\n")
    _open_command_pipe()
    if _nagios_command_pipe is not None and not isinstance(_nagios_command_pipe, bool):
        # [<timestamp>] PROCESS_SERVICE_CHECK_RESULT;<host_name>;<svc_description>;<return_code>;<plugin_output>
        msg = "[%d] PROCESS_SERVICE_CHECK_RESULT;%s;%s;%d;%s\n" % (time.time(), host, service,
                                                                   state, output)
        _nagios_command_pipe.write(ensure_binary(msg))
        # Important: Nagios needs the complete command in one single write() block!
        # Python buffers and sends chunks of 4096 bytes, if we do not flush.
        _nagios_command_pipe.flush()


def _open_command_pipe() -> None:
    global _nagios_command_pipe
    if _nagios_command_pipe is None:
        if not os.path.exists(cmk.utils.paths.nagios_command_pipe_path):
            _nagios_command_pipe = False  # False means: tried but failed to open
            raise MKGeneralException("Missing core command pipe '%s'" %
                                     cmk.utils.paths.nagios_command_pipe_path)
        try:
            signal.signal(signal.SIGALRM, _core_pipe_open_timeout)
            signal.alarm(3)  # three seconds to open pipe
            _nagios_command_pipe = open(cmk.utils.paths.nagios_command_pipe_path, 'wb')
            signal.alarm(0)  # cancel alarm
        except Exception as e:
            _nagios_command_pipe = False
            raise MKGeneralException("Error writing to command pipe: %s" % e)


def _core_pipe_open_timeout(signum: int, stackframe: Optional[FrameType]) -> None:
    raise IOError("Timeout while opening pipe")


#.
#   .--Misc----------------------------------------------------------------.
#   |                          __  __ _                                    |
#   |                         |  \/  (_)___  ___                           |
#   |                         | |\/| | / __|/ __|                          |
#   |                         | |  | | \__ \ (__                           |
#   |                         |_|  |_|_|___/\___|                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Various helper functions                                             |
#   '----------------------------------------------------------------------'


def show_perfdata() -> None:
    global _show_perfdata
    _show_perfdata = True


def disable_submit() -> None:
    global _submit_to_core
    _submit_to_core = False


def _in_keepalive_mode() -> bool:
    if keepalive:
        return keepalive.enabled()
    return False
