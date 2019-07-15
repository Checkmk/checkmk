#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Performing the actual checks."""

import os
import signal
import tempfile
import time
import copy
from typing import List, Tuple, Optional  # pylint: disable=unused-import

import six

import cmk
import cmk.utils.defines as defines
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException, MKTimeout
from cmk.utils.regex import regex
import cmk.utils.debug

import cmk_base.utils
import cmk_base.crash_reporting
import cmk_base.console as console
import cmk_base.config as config
import cmk_base.cpu_tracking as cpu_tracking
import cmk_base.ip_lookup as ip_lookup
import cmk_base.data_sources as data_sources
import cmk_base.item_state as item_state
import cmk_base.check_table as check_table
from cmk_base.exceptions import MKParseFunctionError
import cmk_base.check_utils
import cmk_base.decorator
import cmk_base.check_api_utils as check_api_utils

try:
    import cmk_base.cee.keepalive as keepalive
    import cmk_base.cee.inline_snmp as inline_snmp
except Exception:
    keepalive = None  # type: ignore
    inline_snmp = None  # type: ignore

# global variables used to cache temporary values that do not need
# to be reset after a configuration change.
_nagios_command_pipe = None  # Filedescriptor to open nagios command pipe.
_checkresult_file_fd = None
_checkresult_file_path = None

_submit_to_core = True
_show_perfdata = False

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


@cmk_base.decorator.handle_check_mk_check_result("mk", "Check_MK")
def do_check(hostname, ipaddress, only_check_plugin_names=None):
    cpu_tracking.start("busy")
    console.verbose("Check_MK version %s\n" % cmk.__version__)

    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    exit_spec = host_config.exit_code_spec()

    status, infotexts, long_infotexts, perfdata = 0, [], [], []
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
                perfdata.extend(source_perfdata)

        if missing_sections and num_success > 0:
            missing_sections_status, missing_sections_infotext = \
                _check_missing_sections(missing_sections, exit_spec)
            status = max(status, missing_sections_status)
            infotexts.append(missing_sections_infotext)

        elif missing_sections:
            infotexts.append("Got no information from host")
            status = max(status, exit_spec.get("empty_output", 2))

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

        if config.record_inline_snmp_stats \
           and host_config.snmp_config(ipaddress).is_inline_snmp_host:
            inline_snmp.save_snmp_stats()


def _check_missing_sections(missing_sections, exit_spec):
    specific_missing_sections_spec = exit_spec.get("specific_missing_sections", [])
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

    generic_missing_sections_status = exit_spec.get("missing_sections", 1)
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
    # type: (data_sources.DataSources, config.HostConfig, Optional[str], Optional[List[str]]) -> Tuple[int, List[str]]
    hostname = host_config.hostname
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
            missing_sections.add(cmk_base.check_utils.section_name_of(service.check_plugin_name))

    import cmk_base.inventory as inventory
    inventory.do_inventory_actions_during_checking_for(sources, multi_host_sections, host_config,
                                                       ipaddress)

    missing_section_list = sorted(list(missing_sections))
    return num_success, missing_section_list


def execute_check(config_cache, multi_host_sections, hostname, ipaddress, check_plugin_name, item,
                  params, description):
    # Make a bit of context information globally available, so that functions
    # called by checks now this context
    check_api_utils.set_service(check_plugin_name, description)
    item_state.set_item_state_prefix(check_plugin_name, item)

    # Skip checks that are not in their check period
    period = config_cache.check_period_of_service(hostname, description)
    if period is not None:
        if not cmk_base.core.check_timeperiod(period):
            console.verbose("Skipping service %s: currently not in timeperiod %s.\n" %
                            (description, period))
            return None
        console.vverbose("Service %s: timeperiod %s is currently active.\n" % (description, period))

    section_name = cmk_base.check_utils.section_name_of(check_plugin_name)

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
            raise x[0], x[1], x[2]

        # TODO: Move this to a helper function
        if section_content is None:  # No data for this check type
            return False

        # In case of SNMP checks but missing agent response, skip this check.
        # Special checks which still need to be called even with empty data
        # may declare this.
        if not section_content and cmk_base.check_utils.is_snmp_check(check_plugin_name) \
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
                                       cmk_base.check_utils.is_snmp_check(check_plugin_name))
        item_state.raise_counter_wrap()

    except item_state.MKCounterWrapped as e:
        # handle check implementations that do not yet support the
        # handling of wrapped counters via exception on their own.
        # Do not submit any check result in that case:
        console.verbose("%-20s PEND - Cannot compute check result: %s\n" % (description, e))
        dont_submit = True

    except MKTimeout:
        raise

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        result = 3, cmk_base.crash_reporting.create_crash_dump(
            hostname, check_plugin_name, item, is_manual_check(hostname, check_plugin_name, item),
            params, description, section_content), []

    if not dont_submit:
        # Now add information about the age of the data in the agent
        # sections. This is in data_sources.g_agent_cache_info. For clusters we
        # use the oldest of the timestamps, of course.
        oldest_cached_at = None
        largest_interval = None

        def minn(a, b):
            if a is None:
                return b
            elif b is None:
                return a
            return min(a, b)

        for host_sections in multi_host_sections.get_host_sections().values():
            section_entries = host_sections.cache_info
            if section_name in section_entries:
                cached_at, cache_interval = section_entries[section_name]
                oldest_cached_at = minn(oldest_cached_at, cached_at)
                largest_interval = max(largest_interval, cache_interval)

        _submit_check_result(hostname,
                             description,
                             result,
                             cached_at=oldest_cached_at,
                             cache_interval=largest_interval)
    return True


def determine_check_params(entries):
    if not isinstance(entries, cmk_base.config.TimespecificParamList):
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
    timespecific_entries = {}
    for entry in entries[::-1]:
        timespecific_entries.update(_evaluate_timespecific_entry(entry))

    return timespecific_entries


def _evaluate_timespecific_entry(entry):
    # Dictionary entries without timespecific settings
    if "tp_default_value" not in entry:
        return entry

    # Timespecific entry, start with default value and update with timespecific entry
    # Note: This combined_entry may be a dict or tuple, so the update mechanism must handle this correctly
    # A shallow copy is sufficient
    combined_entry = copy.copy(entry["tp_default_value"])
    for timeperiod_name, tp_entry in entry["tp_values"][::-1]:
        try:
            tp_active = cmk_base.core.timeperiod_active(timeperiod_name)
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
    manual_checks = check_table.get_check_table(hostname,
                                                remove_duplicates=True,
                                                skip_autochecks=True)
    return (check_plugin_name, item) in manual_checks


def sanitize_check_result(result, is_snmp):
    if isinstance(result, tuple):
        return _sanitize_tuple_check_result(result)

    elif result is None:
        return _item_not_found(is_snmp)

    return _sanitize_yield_check_result(result, is_snmp)


# The check function may return an iterator (using yield) since 1.2.5i5.
# This function handles this case and converts them to tuple results
def _sanitize_yield_check_result(result, is_snmp):
    subresults = list(result)

    # Empty list? Check returned nothing
    if not subresults:
        return _item_not_found(is_snmp)

    # Several sub results issued with multiple yields. Make that worst sub check
    # decide the total state, join the texts and performance data. Subresults with
    # an infotext of None are used for adding performance data.
    perfdata = []
    infotexts = []
    status = 0

    for subresult in subresults:
        st, text, perf = _sanitize_tuple_check_result(subresult, allow_missing_infotext=True)
        status = cmk_base.utils.worst_service_state(st, status)

        if text:
            infotexts.append(text + ["", "(!)", "(!!)", "(?)"][st])

        if perf is not None:
            perfdata += perf

    return status, ", ".join(infotexts), perfdata


def _item_not_found(is_snmp):
    if is_snmp:
        return 3, "Item not found in SNMP data", []

    return 3, "Item not found in agent output", []


def _sanitize_tuple_check_result(result, allow_missing_infotext=False):
    if len(result) >= 3:
        state, infotext, perfdata = result[:3]
        _validate_perf_data_values(perfdata)
    else:
        state, infotext = result
        perfdata = None

    infotext = _sanitize_check_result_infotext(infotext, allow_missing_infotext)

    return state, infotext, perfdata


def _validate_perf_data_values(perfdata):
    if not isinstance(perfdata, list):
        return
    for v in [value for entry in perfdata for value in entry[1:]]:
        if " " in str(v):
            # See Nagios performance data spec for detailed information
            raise MKGeneralException("Performance data values must not contain spaces")


def _sanitize_check_result_infotext(infotext, allow_missing_infotext):
    if infotext is None and not allow_missing_infotext:
        raise MKGeneralException("Invalid infotext from check: \"None\"")

    if isinstance(infotext, str):
        return infotext.decode('utf-8')

    return infotext


def _convert_perf_data(p):
    # replace None with "" and fill up to 7 values
    p = (map(_convert_perf_value, p) + ['', '', '', ''])[0:6]
    return "%s=%s;%s;%s;%s;%s" % tuple(p)


def _convert_perf_value(x):
    if x is None:
        return ""
    elif isinstance(x, six.string_types):
        return x
    elif isinstance(x, float):
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
    if not result:
        result = 3, "Check plugin did not return any result"

    if len(result) != 3:
        raise MKGeneralException("Invalid check result: %s" % (result,))
    state, infotext, perfdata = result

    if not (infotext.startswith("OK -") or infotext.startswith("WARN -") or
            infotext.startswith("CRIT -") or infotext.startswith("UNKNOWN -")):
        infotext = defines.short_service_state_name(state) + " - " + infotext

    # make sure that plugin output does not contain a vertical bar. If that is the
    # case then replace it with a Uniocode "Light vertical bar
    if isinstance(infotext, unicode):
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
    if _show_perfdata:
        infotext_fmt = "%-56s"
        p = ' (%s)' % (" ".join(perftexts))
    else:
        p = ''
        infotext_fmt = "%s"

    console.verbose("%-20s %s%s" + infotext_fmt + "%s%s\n",
                    servicedesc.encode('utf-8'), tty.bold, tty.states[state],
                    cmk_base.utils.make_utf8(infotext.split('\n')[0]), tty.normal,
                    cmk_base.utils.make_utf8(p))


def _do_submit_to_core(host, service, state, output, cached_at=None, cache_interval=None):
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
    output = output.replace("\n", "\\n")
    _open_checkresult_file()
    if _checkresult_file_fd:
        now = time.time()
        os.write(
            _checkresult_file_fd, """host_name=%s
service_description=%s
check_type=1
check_options=0
reschedule_check
latency=0.0
start_time=%.1f
finish_time=%.1f
return_code=%d
output=%s

""" % (host, cmk_base.utils.make_utf8(service), now, now, state, cmk_base.utils.make_utf8(output)))


def _open_checkresult_file():
    global _checkresult_file_fd
    global _checkresult_file_path
    if _checkresult_file_fd is None:
        try:
            _checkresult_file_fd, _checkresult_file_path = \
                tempfile.mkstemp('', 'c', cmk.utils.paths.check_result_path)
        except Exception as e:
            raise MKGeneralException("Cannot create check result file in %s: %s" %
                                     (cmk.utils.paths.check_result_path, e))


def _close_checkresult_file():
    global _checkresult_file_fd
    if _checkresult_file_fd is not None:
        os.close(_checkresult_file_fd)
        file(_checkresult_file_path + ".ok", "w")
        _checkresult_file_fd = None


def _submit_via_command_pipe(host, service, state, output):
    output = output.replace("\n", "\\n")
    _open_command_pipe()
    if _nagios_command_pipe:
        # [<timestamp>] PROCESS_SERVICE_CHECK_RESULT;<host_name>;<svc_description>;<return_code>;<plugin_output>
        _nagios_command_pipe.write("[%d] PROCESS_SERVICE_CHECK_RESULT;%s;%s;%d;%s\n" %
                                   (int(time.time()), host, cmk_base.utils.make_utf8(service),
                                    state, cmk_base.utils.make_utf8(output)))
        # Important: Nagios needs the complete command in one single write() block!
        # Python buffers and sends chunks of 4096 bytes, if we do not flush.
        _nagios_command_pipe.flush()


def _open_command_pipe():
    global _nagios_command_pipe
    if _nagios_command_pipe is None:
        if not os.path.exists(cmk.utils.paths.nagios_command_pipe_path):
            _nagios_command_pipe = False  # False means: tried but failed to open
            raise MKGeneralException("Missing core command pipe '%s'" %
                                     cmk.utils.paths.nagios_command_pipe_path)
        else:
            try:
                signal.signal(signal.SIGALRM, _core_pipe_open_timeout)
                signal.alarm(3)  # three seconds to open pipe
                _nagios_command_pipe = file(cmk.utils.paths.nagios_command_pipe_path, 'w')
                signal.alarm(0)  # cancel alarm
            except Exception as e:
                _nagios_command_pipe = False
                raise MKGeneralException("Error writing to command pipe: %s" % e)


def _core_pipe_open_timeout(signum, stackframe):
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
    global _show_perfdata
    _show_perfdata = True


def disable_submit():
    global _submit_to_core
    _submit_to_core = False


def _in_keepalive_mode():
    if keepalive:
        return keepalive.enabled()
    return False
