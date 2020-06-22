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
    Tuple,
    Union,
)

from six import ensure_binary, ensure_str

import cmk.utils.debug
import cmk.utils.defines as defines
import cmk.utils.tty as tty
import cmk.utils.version as cmk_version
from cmk.utils.check_utils import section_name_of
from cmk.utils.exceptions import MKGeneralException, MKTimeout
from cmk.utils.log import console
from cmk.utils.regex import regex
from cmk.utils.type_defs import (
    CheckPluginName,
    HostAddress,
    HostName,
    Item,
    Metric,
    PluginName,
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
import cmk.base.ip_lookup as ip_lookup
import cmk.base.item_state as item_state
import cmk.base.utils
from cmk.base.api.agent_based import checking_types, value_store
from cmk.base.api.agent_based.register.check_plugins_legacy import (
    CLUSTER_LEGACY_MODE_FROM_HELL,
    maincheckify,
    wrap_parameters,
)
from cmk.base.check_utils import CheckParameters, Service
from cmk.base.exceptions import MKParseFunctionError

if not cmk_version.is_raw_edition():
    import cmk.base.cee.keepalive as keepalive  # type: ignore[import] # pylint: disable=no-name-in-module
    from cmk.fetchers.cee.snmp_backend import inline  # type: ignore[import] # pylint: disable=no-name-in-module, import-error, cmk-module-layer-violation
else:
    keepalive = None  # type: ignore[assignment]
    inline = None  # type: ignore[assignment]

# global variables used to cache temporary values that do not need
# to be reset after a configuration change.
# Filedescriptor to open nagios command pipe.
_nagios_command_pipe = None  # type: Union[bool, IO[bytes], None]
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

ITEM_NOT_FOUND = (3, "Item not found in monitoring data", [])  # type: ServiceCheckResult

RECEIVED_NO_DATA = (3, "Check plugin received no monitoring data", [])  # type: ServiceCheckResult

CHECK_NOT_IMPLEMENTED = (3, 'Check plugin not implemented', [])  # type: ServiceCheckResult


@cmk.base.decorator.handle_check_mk_check_result("mk", "Check_MK")
def do_check(hostname, ipaddress, only_check_plugin_names=None):
    # type: (HostName, Optional[HostAddress], Optional[List[CheckPluginName]]) -> Tuple[int, List[ServiceDetails], List[ServiceAdditionalDetails], List[str]]
    cpu_tracking.start("busy")
    console.verbose("Check_MK version %s\n", cmk_version.__version__)

    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    exit_spec = host_config.exit_code_spec()

    status = 0  # type: ServiceState
    infotexts = []  # type: List[ServiceDetails]
    long_infotexts = []  # type: List[ServiceAdditionalDetails]
    perfdata = []  # type: List[str]
    try:
        # In case of keepalive we always have an ipaddress (can be 0.0.0.0 or :: when
        # address is unknown). When called as non keepalive ipaddress may be None or
        # is already an address (2nd argument)
        if ipaddress is None and not host_config.is_cluster:
            ipaddress = ip_lookup.lookup_ip_address(hostname)

        item_state.load(hostname)

        sources = data_sources.DataSources(hostname, ipaddress)

        num_success, missing_sections = \
            _do_all_checks_on_host(sources, host_config, ipaddress, only_check_plugin_names)

        if _submit_to_core:
            item_state.save(hostname)

        for source in sources.get_data_sources():
            source_state, source_output, source_perfdata = source.get_summary_result_for_checking()
            if source_output != "":
                status = max(status, source_state)
                infotexts.append("[%s] %s" % (source.id(), source_output))
                perfdata.extend([_convert_perf_data(p) for p in source_perfdata])

        if missing_sections and num_success > 0:
            missing_sections_status, missing_sections_infotext = \
                _check_missing_sections(missing_sections, exit_spec)
            status = max(status, missing_sections_status)
            infotexts.append(missing_sections_infotext)

        elif missing_sections:
            infotexts.append("Got no information from host")
            status = max(status, cast(int, exit_spec.get("empty_output", 2)))

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


def _check_missing_sections(missing_sections, exit_spec):
    # type: (List[SectionName], config.ExitSpec) -> Tuple[ServiceState, ServiceDetails]
    specific_missing_sections_spec = \
        cast(List[config.ExitSpecSection], exit_spec.get("specific_missing_sections", []))

    specific_missing_sections, generic_missing_sections = set(), set()
    for section in missing_sections:
        match = False
        for pattern, status in specific_missing_sections_spec:
            reg = regex(pattern)
            if reg.match(section):
                match = True
                specific_missing_sections.add((section, status))
                break
        if not match:
            generic_missing_sections.add(section)

    generic_missing_sections_status = cast(int, exit_spec.get("missing_sections", 1))
    infotexts = [
        "Missing agent sections: %s%s" %
        (", ".join(sorted(generic_missing_sections)),
         check_api_utils.state_markers[generic_missing_sections_status])
    ]

    for section, status in sorted(specific_missing_sections):
        infotexts.append("%s%s" % (section, check_api_utils.state_markers[status]))
        generic_missing_sections_status = max(generic_missing_sections_status, status)

    return generic_missing_sections_status, ", ".join(infotexts)


# Loops over all checks for ANY host (cluster, real host), gets the data, calls the check
# function that examines that data and sends the result to the Core.
def _do_all_checks_on_host(sources, host_config, ipaddress, only_check_plugin_names=None):
    # type: (data_sources.DataSources, config.HostConfig, Optional[HostAddress], Optional[List[str]]) -> Tuple[int, List[SectionName]]
    hostname = host_config.hostname  # type: HostName
    config_cache = config.get_config_cache()

    num_success, missing_sections = 0, set()

    check_api_utils.set_hostname(hostname)

    belongs_to_cluster = len(config_cache.clusters_of(hostname)) > 0

    services = check_table.get_precompiled_check_table(
        hostname,
        remove_duplicates=True,
        filter_mode="include_clustered" if belongs_to_cluster else None,
    )

    # When check types are specified via command line, enforce them. Otherwise use the
    # list of checks defined by the check table.
    if only_check_plugin_names is None:
        only_check_plugins = {service.check_plugin_name for service in services}
    else:
        only_check_plugins = set(only_check_plugin_names)

    sources.enforce_check_plugin_names(only_check_plugins)

    # Gather the data from the sources
    multi_host_sections = sources.get_host_sections()

    def _is_not_of_host(host_name, service):
        return hostname != config_cache.host_of_clustered_service(hostname, service.description)

    # Filter out check types which are not used on the node
    if belongs_to_cluster:
        removed_plugins = {
            plugin for plugin in only_check_plugins if all(
                _is_not_of_host(hostname, service) for service in services
                if service.check_plugin_name == plugin)
        }
        only_check_plugins -= removed_plugins

    for service in services:
        if service.check_plugin_name not in only_check_plugins:
            continue
        if belongs_to_cluster and _is_not_of_host(hostname, service):
            continue
        if service_outside_check_period(config_cache, hostname, service.description):
            continue

        success = execute_check(multi_host_sections, host_config, ipaddress, service)
        if success:
            num_success += 1
        else:
            missing_sections.add(section_name_of(service.check_plugin_name))

    import cmk.base.inventory as inventory  # pylint: disable=import-outside-toplevel
    inventory.do_inventory_actions_during_checking_for(sources, multi_host_sections, host_config,
                                                       ipaddress)

    missing_section_list = sorted(missing_sections)
    return num_success, missing_section_list


def service_outside_check_period(config_cache, hostname, description):
    # type: (config.ConfigCache, HostName, ServiceName) -> bool
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


def execute_check(multi_host_sections, host_config, ipaddress, service):
    # type: (data_sources.MultiHostSections, config.HostConfig, Optional[HostAddress], Service) -> bool
    # TODO (mo): centralize maincheckify: CMK-4295
    plugin_name = PluginName(maincheckify(service.check_plugin_name))
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
    multi_host_sections: data_sources.MultiHostSections,
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    service: Service,
    plugin: Optional[checking_types.CheckPlugin],
    params_function: Callable[[], checking_types.Parameters],
) -> Tuple[bool, bool, ServiceCheckResult]:
    if plugin is None:
        return False, True, CHECK_NOT_IMPLEMENTED

    check_function = (plugin.cluster_check_function
                      if host_config.is_cluster else plugin.check_function)

    source_type = (SourceType.MANAGEMENT
                   if service.check_plugin_name.startswith('mgmt_') else SourceType.HOST)
    kwargs = {}
    try:
        kwargs = multi_host_sections.get_section_cluster_kwargs(
            host_config.hostname,
            source_type,
            plugin.sections,
            service.description,
        ) if host_config.is_cluster else multi_host_sections.get_section_kwargs(
            (host_config.hostname, ipaddress, source_type),
            plugin.sections,
        )

        if not kwargs:
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
            is_manual_check(host_config.hostname, service.check_plugin_name, service.item),
            service.description,
        ), []

    return True, True, result


def _execute_check_legacy_mode(multi_host_sections, hostname, ipaddress, service):
    # type: (data_sources.MultiHostSections, HostName, Optional[HostAddress], Service) -> bool
    check_function = config.check_info[service.check_plugin_name].get("check_function")
    if check_function is None:
        _submit_check_result(hostname, service.description, CHECK_NOT_IMPLEMENTED, None)
        return True
    # Make a bit of context information globally available, so that functions
    # called by checks know this context
    check_api_utils.set_service(service.check_plugin_name, service.description)
    item_state.set_item_state_prefix(service.check_plugin_name, service.item)

    section_name = section_name_of(service.check_plugin_name)

    section_content = None
    try:
        # TODO: There is duplicate code with discovery._execute_discovery(). Find a common place!
        try:
            section_content = multi_host_sections.get_section_content(
                hostname,
                ipaddress,
                config.get_management_board_precedence(section_name, config.check_info),
                section_name,
                for_discovery=False,
                service_description=service.description)
        except MKParseFunctionError as e:
            x = e.exc_info()
            # re-raise the original exception to not destory the trace. This may raise a MKCounterWrapped
            # exception which need to lead to a skipped check instead of a crash
            # TODO CMK-3729, PEP-3109
            new_exception = x[0](x[1])
            new_exception.__traceback__ = x[2]  # type: ignore[attr-defined]
            raise new_exception

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
            is_manual_check(hostname, service.check_plugin_name, service.item),
            service.description,
        ), []

    _submit_check_result(
        hostname,
        service.description,
        result,
        _legacy_determine_cache_info(multi_host_sections, section_name),
    )
    return True


def _legacy_determine_cache_info(multi_host_sections, section_name):
    # type: (data_sources.MultiHostSections, SectionName) -> Optional[Tuple[int, int]]
    """Aggregate information about the age of the data in the agent sections

    This is in data_sources.g_agent_cache_info. For clusters we use the oldest
    of the timestamps, of course.
    """
    cached_ats = []  # type: List[int]
    intervals = []  # type: List[int]
    for host_sections in multi_host_sections.get_host_sections().values():
        section_entries = host_sections.cache_info
        if section_name in section_entries:
            cached_at, cache_interval = section_entries[section_name]
            cached_ats.append(cached_at)
            intervals.append(cache_interval)

    return (min(cached_ats), max(intervals)) if cached_ats else None


def determine_check_params(entries):
    # type: (CheckParameters) -> checking_types.Parameters
    # TODO (mo): obviously, we do not want to keep legacy_determine_check_params
    # around in the long run. This needs cleaning up, once we've gotten
    # rid of tuple parameters.
    params = legacy_determine_check_params(entries)
    # wrap_parameters is a no-op for dictionaries.
    # For auto-migrated plugins expecting tuples, they will be
    # unwrapped by a decorator of the original check_function.
    return checking_types.Parameters(wrap_parameters(params))


def legacy_determine_check_params(entries):
    # type: (CheckParameters) -> CheckParameters
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
    timespecific_entries = {}  # type: Dict[str, Any]
    for entry in entries[::-1]:
        if not isinstance(entry, dict):
            # Ignore (old) default parameters like
            #   'NAME_default_levels' = (80.0, 85.0)
            # A rule with a timespecifc parameter settings always has an
            # implicit default parameter set, even if no timeperiod matches.
            continue
        timespecific_entries.update(_evaluate_timespecific_entry(entry))

    return timespecific_entries


def _evaluate_timespecific_entry(entry):
    # type: (Dict[str, Any]) -> Dict[str, Any]
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


def is_manual_check(hostname, check_plugin_name, item):
    # type: (HostName, CheckPluginName, Item) -> bool
    manual_checks = check_table.get_check_table(hostname,
                                                remove_duplicates=True,
                                                skip_autochecks=True)
    return (check_plugin_name, item) in manual_checks


def _aggregate_results(subresults):
    # type: (Iterable[Union[checking_types.Metric, checking_types.Result, checking_types.IgnoreResults]]) -> ServiceCheckResult
    perfdata = []  # type: List[Metric]
    summaries = []  # type: List[str]
    details = []  # type: List[str]
    status = checking_types.state(0)

    for subr in list(subresults):  # consume *everything* here, before we may raise!
        if isinstance(subr, checking_types.IgnoreResults):
            raise checking_types.IgnoreResultsError(str(subr))
        if isinstance(subr, checking_types.Metric):
            perfdata.append((subr.name, subr.value) + subr.levels + subr.boundaries)
            continue

        status = checking_types.state_worst(status, subr.state)
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


def sanitize_check_result(result):
    # type: (Union[None, ServiceCheckResult, Tuple, Iterable]) -> ServiceCheckResult
    if isinstance(result, tuple):
        return cast(ServiceCheckResult, _sanitize_tuple_check_result(result))

    if result is None:
        return ITEM_NOT_FOUND

    return _sanitize_yield_check_result(result)


# The check function may return an iterator (using yield) since 1.2.5i5.
# This function handles this case and converts them to tuple results
def _sanitize_yield_check_result(result):
    # type: (Iterable[Any]) -> ServiceCheckResult
    subresults = list(result)

    # Empty list? Check returned nothing
    if not subresults:
        return ITEM_NOT_FOUND

    # Several sub results issued with multiple yields. Make that worst sub check
    # decide the total state, join the texts and performance data. Subresults with
    # an infotext of None are used for adding performance data.
    perfdata = []  # type: List[Metric]
    infotexts = []  # type: List[ServiceDetails]
    status = 0  # type: ServiceState

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
def _sanitize_tuple_check_result(result, allow_missing_infotext=False):
    # type: (Tuple, bool) -> ServiceCheckResultWithOptionalDetails
    if len(result) >= 3:
        state, infotext, perfdata = result[:3]
        _validate_perf_data_values(perfdata)
    else:
        state, infotext = result
        perfdata = []

    infotext = _sanitize_check_result_infotext(infotext, allow_missing_infotext)

    return state, infotext, perfdata


def _validate_perf_data_values(perfdata):
    # type: (Any) -> None
    if not isinstance(perfdata, list):
        return
    for v in [value for entry in perfdata for value in entry[1:]]:
        if " " in str(v):
            # See Nagios performance data spec for detailed information
            raise MKGeneralException("Performance data values must not contain spaces")


def _sanitize_check_result_infotext(infotext, allow_missing_infotext):
    # type: (Optional[AnyStr], bool) -> Optional[ServiceDetails]
    if infotext is None and not allow_missing_infotext:
        raise MKGeneralException("Invalid infotext from check: \"None\"")

    if isinstance(infotext, bytes):
        return infotext.decode('utf-8')

    return infotext


def _convert_perf_data(p):
    # type: (List[UncleanPerfValue]) -> str
    # replace None with "" and fill up to 6 values
    normalized = (list(map(_convert_perf_value, p)) + ['', '', '', ''])[0:6]
    return "%s=%s;%s;%s;%s;%s" % tuple(normalized)


def _convert_perf_value(x):
    # type: (UncleanPerfValue) -> str
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


def _submit_check_result(host, servicedesc, result, cache_info):
    # type: (HostName, ServiceDetails, ServiceCheckResult, Optional[Tuple[int, int]]) -> None
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


def _output_check_result(servicedesc, state, infotext, perftexts):
    # type: (ServiceName, ServiceState, ServiceDetails, List[str]) -> None
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
        host,  # type: HostName
        service,  # type: ServiceName
        state,  # type: ServiceState
        output,  # type: ServiceDetails
        cache_info,  # type: Optional[Tuple[int, int]]
):
    # type: (...) -> None
    if _in_keepalive_mode():
        cached_at, cache_interval = cache_info or (None, None)
        # Regular case for the CMC - check helpers are running in keepalive mode
        keepalive.add_keepalive_check_result(host, service, state, output, cached_at,
                                             cache_interval)

    elif config.check_submission == "pipe" or config.monitoring_core == "cmc":
        # In case of CMC this is used when running "cmk" manually
        _submit_via_command_pipe(host, service, state, output)

    elif config.check_submission == "file":
        _submit_via_check_result_file(host, service, state, output)

    else:
        raise MKGeneralException("Invalid setting %r for check_submission. "
                                 "Must be 'pipe' or 'file'" % config.check_submission)


def _submit_via_check_result_file(host, service, state, output):
    # type: (HostName, ServiceName, ServiceState, ServiceDetails) -> None
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


def _open_checkresult_file():
    # type: () -> None
    global _checkresult_file_fd
    global _checkresult_file_path
    if _checkresult_file_fd is None:
        try:
            _checkresult_file_fd, _checkresult_file_path = _create_nagios_check_result_file()
        except Exception as e:
            raise MKGeneralException("Cannot create check result file in %s: %s" %
                                     (cmk.utils.paths.check_result_path, e))


def _create_nagios_check_result_file():
    # type: () -> Tuple[int, str]
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


_name_sequence = None  # type: Optional[_RandomNameSequence]


def _get_candidate_names():
    # type: () -> _RandomNameSequence
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
    def rng(self):
        # type: () -> Random
        cur_pid = os.getpid()
        if cur_pid != getattr(self, '_rng_pid', None):
            self._rng = Random()
            self._rng_pid = cur_pid
        return self._rng

    def __iter__(self):
        # type: () -> _RandomNameSequence
        return self

    def __next__(self):
        # type: () -> str
        c = self.characters
        choose = self.rng.choice
        letters = [choose(c) for dummy in range(6)]
        return ''.join(letters)


def _close_checkresult_file():
    # type: () -> None
    global _checkresult_file_fd
    if _checkresult_file_fd is not None and _checkresult_file_path is not None:
        os.close(_checkresult_file_fd)
        _checkresult_file_fd = None

        with open(_checkresult_file_path + ".ok", "w"):
            pass


def _submit_via_command_pipe(host, service, state, output):
    # type: (HostName, ServiceName, ServiceState, ServiceDetails) -> None
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


def _open_command_pipe():
    # type: () -> None
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


def _core_pipe_open_timeout(signum, stackframe):
    # type: (int, Optional[FrameType]) -> None
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


def show_perfdata():
    # type: () -> None
    global _show_perfdata
    _show_perfdata = True


def disable_submit():
    # type: () -> None
    global _submit_to_core
    _submit_to_core = False


def _in_keepalive_mode():
    # type: () -> bool
    if keepalive:
        return keepalive.enabled()
    return False
