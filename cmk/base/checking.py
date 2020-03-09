#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Performing the actual checks."""

import os
import signal
from random import Random
import time
import copy
import errno
from types import FrameType  # pylint: disable=unused-import
from typing import (  # pylint: disable=unused-import
    cast, IO, Union, Any, AnyStr, List, Tuple, Optional, Text, Iterable, Dict,
)

import six

import cmk
import cmk.utils.defines as defines
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException, MKTimeout
from cmk.utils.regex import regex
import cmk.utils.debug

import cmk.base.utils
import cmk.base.core
import cmk.base.crash_reporting
import cmk.base.console as console
import cmk.base.config as config
import cmk.base.cpu_tracking as cpu_tracking
import cmk.base.ip_lookup as ip_lookup
import cmk.base.data_sources as data_sources
import cmk.base.item_state as item_state
import cmk.base.check_table as check_table
from cmk.base.exceptions import MKParseFunctionError
import cmk.base.check_utils
import cmk.base.decorator
import cmk.base.check_api_utils as check_api_utils
from cmk.base.check_utils import (  # pylint: disable=unused-import
    ServiceState, ServiceDetails, ServiceAdditionalDetails, ServiceCheckResult, Metric,
    CheckPluginName, Item, SectionName, CheckParameters,
)
from cmk.utils.type_defs import HostName, HostAddress, ServiceName  # pylint: disable=unused-import

if not cmk.is_raw_edition():
    import cmk.base.cee.keepalive as keepalive  # pylint: disable=no-name-in-module
    import cmk.base.cee.inline_snmp as inline_snmp  # pylint: disable=no-name-in-module
else:
    keepalive = None  # type: ignore[assignment]
    inline_snmp = None  # type: ignore[assignment]

# global variables used to cache temporary values that do not need
# to be reset after a configuration change.
# Filedescriptor to open nagios command pipe.
_nagios_command_pipe = None  # type: Union[bool, IO[bytes], None]
_checkresult_file_fd = None
_checkresult_file_path = None

_submit_to_core = True
_show_perfdata = False

ServiceCheckResultWithOptionalDetails = Tuple[ServiceState, ServiceDetails, List[Metric]]
UncleanPerfValue = Optional[Union[str, float]]

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


@cmk.base.decorator.handle_check_mk_check_result("mk", "Check_MK")
def do_check(hostname, ipaddress, only_check_plugin_names=None):
    # type: (HostName, Optional[HostAddress], Optional[List[CheckPluginName]]) -> Tuple[int, List[ServiceDetails], List[ServiceAdditionalDetails], List[Text]]
    cpu_tracking.start("busy")
    console.verbose("Check_MK version %s\n", six.ensure_str(cmk.__version__))

    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    exit_spec = host_config.exit_code_spec()

    status = 0  # type: ServiceState
    infotexts = []  # type: List[ServiceDetails]
    long_infotexts = []  # type: List[ServiceAdditionalDetails]
    perfdata = []  # type: List[Text]
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
            inline_snmp.save_snmp_stats()


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

    filter_mode = None

    belongs_to_cluster = len(config_cache.clusters_of(hostname)) > 0
    if belongs_to_cluster:
        filter_mode = "include_clustered"

    services = check_table.get_precompiled_check_table(hostname,
                                                       remove_duplicates=True,
                                                       filter_mode=filter_mode)

    # When check types are specified via command line, enforce them. Otherwise use the
    # list of checks defined by the check table.
    if only_check_plugin_names is None:
        only_check_plugins = {service.check_plugin_name for service in services}
    else:
        only_check_plugins = set(only_check_plugin_names)

    sources.enforce_check_plugin_names(only_check_plugins)

    # Gather the data from the sources
    multi_host_sections = sources.get_host_sections()

    # Filter out check types which are not used on the node
    if belongs_to_cluster:
        pos_match = set()
        neg_match = set()
        for service in services:
            if hostname != config_cache.host_of_clustered_service(hostname, service.description):
                pos_match.add(service.check_plugin_name)
            else:
                neg_match.add(service.check_plugin_name)
        only_check_plugins -= (pos_match - neg_match)

    for service in services:
        if only_check_plugins is not None and service.check_plugin_name not in only_check_plugins:
            continue

        if belongs_to_cluster and hostname != config_cache.host_of_clustered_service(
                hostname, service.description):
            continue

        success = execute_check(config_cache, multi_host_sections, hostname, ipaddress,
                                service.check_plugin_name, service.item, service.parameters,
                                service.description)
        if success:
            num_success += 1
        elif success is None:
            # If the service is in any timeperiod we do not want to
            # - increase num_success or
            # - add to missing sections
            continue
        else:
            missing_sections.add(cmk.base.check_utils.section_name_of(service.check_plugin_name))

    import cmk.base.inventory as inventory  # pylint: disable=import-outside-toplevel
    inventory.do_inventory_actions_during_checking_for(sources, multi_host_sections, host_config,
                                                       ipaddress)

    missing_section_list = sorted(missing_sections)
    return num_success, missing_section_list


def execute_check(config_cache, multi_host_sections, hostname, ipaddress, check_plugin_name, item,
                  params, description):
    # type: (config.ConfigCache, data_sources.MultiHostSections, HostName, Optional[HostAddress], CheckPluginName, Item, CheckParameters, ServiceName) -> Optional[bool]
    # Make a bit of context information globally available, so that functions
    # called by checks now this context
    check_api_utils.set_service(check_plugin_name, description)
    item_state.set_item_state_prefix(check_plugin_name, item)

    # Skip checks that are not in their check period
    period = config_cache.check_period_of_service(hostname, description)
    if period is not None:
        if not cmk.base.core.check_timeperiod(period):
            console.verbose("Skipping service %s: currently not in timeperiod %s.\n",
                            six.ensure_str(description), period)
            return None
        console.vverbose("Service %s: timeperiod %s is currently active.\n",
                         six.ensure_str(description), period)

    section_name = cmk.base.check_utils.section_name_of(check_plugin_name)

    dont_submit = False
    section_content = None
    try:
        # TODO: There is duplicate code with discovery._execute_discovery(). Find a common place!
        try:
            section_content = multi_host_sections.get_section_content(
                hostname,
                ipaddress,
                section_name,
                for_discovery=False,
                service_description=description)
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

        # In case of SNMP checks but missing agent response, skip this check.
        # TODO: This feature predates the 'parse_function', and is not needed anymore.
        # # Special checks which still need to be called even with empty data
        # # may declare this.
        if not section_content and cmk.base.check_utils.is_snmp_check(check_plugin_name) \
           and not config.check_info[check_plugin_name]["handle_empty_info"]:
            return False

        check_function = config.check_info[check_plugin_name].get("check_function")
        if check_function is None:
            check_function = lambda item, params, section_content: (
                3, 'UNKNOWN - Check not implemented')

        # Call the actual check function
        item_state.reset_wrapped_counters()

        raw_result = check_function(item, determine_check_params(params), section_content)
        result = sanitize_check_result(raw_result,
                                       cmk.base.check_utils.is_snmp_check(check_plugin_name))
        item_state.raise_counter_wrap()

    except item_state.MKCounterWrapped as e:
        # handle check implementations that do not yet support the
        # handling of wrapped counters via exception on their own.
        # Do not submit any check result in that case:
        console.verbose("%-20s PEND - Cannot compute check result: %s\n",
                        six.ensure_str(description), e)
        dont_submit = True

    except MKTimeout:
        raise

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        result = 3, cmk.base.crash_reporting.create_check_crash_dump(
            hostname, check_plugin_name, item, is_manual_check(hostname, check_plugin_name, item),
            params, description, section_content), []

    if not dont_submit:
        # Now add information about the age of the data in the agent
        # sections. This is in data_sources.g_agent_cache_info. For clusters we
        # use the oldest of the timestamps, of course.
        oldest_cached_at = None
        largest_interval = None

        def minn(a, b):
            # type: (Optional[int], Optional[int]) -> Optional[int]
            if a is None:
                return b
            if b is None:
                return a
            return min(a, b)

        def maxn(a, b):
            # type: (Optional[int], Optional[int]) -> Optional[int]
            if a is None:
                return b
            if b is None:
                return a
            return max(a, b)

        for host_sections in multi_host_sections.get_host_sections().values():
            section_entries = host_sections.cache_info
            if section_name in section_entries:
                cached_at, cache_interval = section_entries[section_name]
                oldest_cached_at = minn(oldest_cached_at, cached_at)
                largest_interval = maxn(largest_interval, cache_interval)

        _submit_check_result(hostname,
                             description,
                             result,
                             cached_at=oldest_cached_at,
                             cache_interval=largest_interval)
    return True


def determine_check_params(entries):
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


def sanitize_check_result(result, is_snmp):
    # type: (Optional[Union[ServiceCheckResult, Tuple, Iterable]], bool) -> ServiceCheckResult
    if isinstance(result, tuple):
        return cast(ServiceCheckResult, _sanitize_tuple_check_result(result))

    if result is None:
        return _item_not_found(is_snmp)

    return _sanitize_yield_check_result(result, is_snmp)


# The check function may return an iterator (using yield) since 1.2.5i5.
# This function handles this case and converts them to tuple results
def _sanitize_yield_check_result(result, is_snmp):
    # type: (Iterable[Any], bool) -> ServiceCheckResult
    subresults = list(result)

    # Empty list? Check returned nothing
    if not subresults:
        return _item_not_found(is_snmp)

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
            infotexts.append(text + ["", "(!)", "(!!)", "(?)"][st])

        if perf is not None:
            perfdata += perf

    return status, ", ".join(infotexts), perfdata


def _item_not_found(is_snmp):
    # type: (bool) -> ServiceCheckResult
    if is_snmp:
        return 3, "Item not found in SNMP data", []

    return 3, "Item not found in agent output", []


# TODO: Cleanup return value: Factor "infotext: Optional[Text]" case out and then make Tuple values
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

    if isinstance(infotext, six.binary_type):
        return infotext.decode('utf-8')

    return infotext


def _convert_perf_data(p):
    # type: (List[UncleanPerfValue]) -> str
    # replace None with "" and fill up to 7 values
    normalized = (list(map(_convert_perf_value, p)) + ['', '', '', ''])[0:6]
    return "%s=%s;%s;%s;%s;%s" % tuple(normalized)


def _convert_perf_value(x):
    # type: (UncleanPerfValue) -> str
    if x is None:
        return ""
    if isinstance(x, six.string_types):
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


def _submit_check_result(host, servicedesc, result, cached_at=None, cache_interval=None):
    # type: (HostName, ServiceDetails, ServiceCheckResult, Optional[int], Optional[int]) -> None
    if not result:
        result = 3, "Check plugin did not return any result"

    if len(result) != 3:
        raise MKGeneralException("Invalid check result: %s" % (result,))
    state, infotext, perfdata = result

    if not (infotext.startswith("OK -") or infotext.startswith("WARN -") or
            infotext.startswith("CRIT -") or infotext.startswith("UNKNOWN -")):
        infotext = defines.short_service_state_name(state) + " - " + infotext

    # make sure that plugin output does not contain a vertical bar. If that is the
    # case then replace it with a Uniocode "Light vertical bar"
    if isinstance(infotext, six.text_type):
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
        if len(perfdata) > 0 and isinstance(perfdata[-1], six.string_types):
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
        _do_submit_to_core(host, servicedesc, state, infotext + perftext, cached_at, cache_interval)

    _output_check_result(servicedesc, state, infotext, perftexts)


def _output_check_result(servicedesc, state, infotext, perftexts):
    # type: (ServiceName, ServiceState, ServiceDetails, List[str]) -> None
    if _show_perfdata:
        infotext_fmt = "%-56s"
        p = ' (%s)' % (" ".join(perftexts))
    else:
        p = ''
        infotext_fmt = "%s"

    console.verbose("%-20s %s%s" + infotext_fmt + "%s%s\n", six.ensure_str(servicedesc), tty.bold,
                    tty.states[state], six.ensure_str(infotext.split('\n')[0]), tty.normal,
                    six.ensure_str(p))


def _do_submit_to_core(host, service, state, output, cached_at=None, cache_interval=None):
    # type: (HostName, ServiceName, ServiceState, ServiceDetails, Optional[int], Optional[int]) -> None
    if _in_keepalive_mode():
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
            six.ensure_binary("""host_name=%s
service_description=%s
check_type=1
check_options=0
reschedule_check
latency=0.0
start_time=%.1f
finish_time=%.1f
return_code=%d
output=%s

""" % (host, six.ensure_str(service), now, now, state, six.ensure_str(output))))


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


class _RandomNameSequence(object):  # pylint: disable=useless-object-inheritance
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
        _nagios_command_pipe.write(six.ensure_binary(msg))
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
