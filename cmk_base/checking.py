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

import cmk
import cmk.defines as defines
import cmk.tty as tty
import cmk.cpu_tracking as cpu_tracking
from cmk.exceptions import MKGeneralException

import cmk_base.utils
import cmk_base.crash_reporting
import cmk_base.console as console
import cmk_base.config as config
import cmk_base.snmp as snmp
import cmk_base.ip_lookup as ip_lookup
import cmk_base.data_sources as data_sources
import cmk_base.item_state as item_state
import cmk_base.core
import cmk_base.check_table as check_table
from cmk_base.exceptions import MKTimeout, MKParseFunctionError
import cmk_base.check_utils
import cmk_base.decorator
import cmk_base.check_api_utils as check_api_utils

try:
    import cmk_base.cee.keepalive as keepalive
except Exception:
    keepalive = None


# global variables used to cache temporary values that do not need
# to be reset after a configuration change.
_nagios_command_pipe   = None # Filedescriptor to open nagios command pipe.
_checkresult_file_fd   = None
_checkresult_file_path = None

_submit_to_core = True
_show_perfdata  = False


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

    # Exit state in various situations is configurable since 1.2.3i1
    exit_spec = config.exit_code_spec(hostname)

    status, infotexts, long_infotexts, perfdata = 0, [], [], []
    try:
        # In case of keepalive we always have an ipaddress (can be 0.0.0.0 or :: when
        # address is unknown). When called as non keepalive ipaddress may be None or
        # is already an address (2nd argument)
        if ipaddress is None and not config.is_cluster(hostname):
            ipaddress = ip_lookup.lookup_ip_address(hostname)

        item_state.load(hostname)

        sources = data_sources.DataSources(hostname, ipaddress)

        num_success, missing_sections = \
            _do_all_checks_on_host(sources, hostname, ipaddress, only_check_plugin_names)

        if _submit_to_core:
            item_state.save(hostname)

        for source in sources.get_data_sources():
            source_state, source_output, source_perfdata = source.get_summary_result()
            if source_output != "":
                status = max(status, source_state)
                infotexts.append("[%s] %s" % (source.id(), source_output))
                perfdata.extend(source_perfdata)

        if missing_sections and num_success > 0:
            infotexts.append("Missing agent sections: %s" % ", ".join(missing_sections))
            status = max(status, exit_spec.get("missing_sections", 1))

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
                if phase in [ "agent", "snmp", "ds" ]:
                    t = times[4] - sum(times[:4]) # real time - CPU time
                    perfdata.append("cmk_time_%s=%.3f" % (phase, t))
        else:
            perfdata.append("execution_time=%.3f" % run_time)

        return status, infotexts, long_infotexts, perfdata
    finally:
        if _checkresult_file_fd != None:
            _close_checkresult_file()

        if config.record_inline_snmp_stats and config.is_inline_snmp_host(hostname):
            import cmk_base.cee.inline_snmp
            cmk_base.cee.inline_snmp.save_snmp_stats()


# Loops over all checks for ANY host (cluster, real host), gets the data, calls the check
# function that examines that data and sends the result to the Core.
def _do_all_checks_on_host(sources, hostname, ipaddress, only_check_plugin_names=None):
    num_success, missing_sections = 0, set()

    check_api_utils.set_hostname(hostname)

    filter_mode = None

    belongs_to_cluster = len(config.clusters_of(hostname)) > 0
    if belongs_to_cluster:
        filter_mode = "include_clustered"

    table = check_table.get_precompiled_check_table(hostname, remove_duplicates=True, filter_mode=filter_mode,
                                    world="active" if _in_keepalive_mode() else "config")

    # When check types are specified via command line, enforce them. Otherwise use the
    # list of checks defined by the check table.
    if only_check_plugin_names is None:
        only_check_plugin_names = set([e[0] for e in table])
    else:
        only_check_plugin_names = set(only_check_plugin_names)

    sources.enforce_check_plugin_names(only_check_plugin_names)

    # Gather the data from the sources
    multi_host_sections = sources.get_host_sections()

    # Filter out check types which are not used on the node
    if belongs_to_cluster:
        pos_match = set()
        neg_match = set()
        for check_plugin_name, item, params, description in table:
            if hostname != config.host_of_clustered_service(hostname, description):
                pos_match.add(check_plugin_name)
            else:
                neg_match.add(check_plugin_name)
        only_check_plugin_names -= (pos_match - neg_match)


    for check_plugin_name, item, params, description in table:
        if only_check_plugin_names != None and check_plugin_name not in only_check_plugin_names:
            continue

        success = execute_check(multi_host_sections, hostname, ipaddress, check_plugin_name, item, params, description)
        if success:
            num_success += 1
        else:
            missing_sections.add(cmk_base.check_utils.section_name_of(check_plugin_name))

    if config.do_status_data_inventory_for(hostname):
        import cmk_base.inventory as inventory
        inventory.do_status_data_inventory(sources, multi_host_sections, hostname, ipaddress)

    missing_section_list = sorted(list(missing_sections))
    return num_success, missing_section_list


def execute_check(multi_host_sections, hostname, ipaddress, check_plugin_name, item, params, description):
    # Make a bit of context information globally available, so that functions
    # called by checks now this context
    check_api_utils.set_service(check_plugin_name, description)
    item_state.set_item_state_prefix(check_plugin_name, item)

    # Skip checks that are not in their check period
    period = config.check_period_of(hostname, description)
    if period and not cmk_base.core.check_timeperiod(period):
        console.verbose("Skipping service %s: currently not in timeperiod %s.\n" % (description, period))
        return False

    elif period:
        console.vverbose("Service %s: timeperiod %s is currently active.\n" % (description, period))

    section_name = cmk_base.check_utils.section_name_of(check_plugin_name)

    # We need to set this again, because get_section_content has the side effect of setting this with
    # item None if there is a parse function. This would break the entire set_item/get_rate logic
    # for checks with items that rely on this being handled by the API.
    # TODO: Write a regression test for this.
    item_state.set_item_state_prefix(check_plugin_name, item)

    dont_submit = False
    section_content = None
    try:
        # TODO: There is duplicate code with discovery._execute_discovery(). Find a common place!
        try:
            section_content = multi_host_sections.get_section_content(hostname,
                                                        ipaddress, section_name, for_discovery=False)
        except MKParseFunctionError, e:
            x = e.exc_info()
            # re-raise the original exception to not destory the trace. This may raise a MKCounterWrapped
            # exception which need to lead to a skipped check instead of a crash
            raise x[0], x[1], x[2]

        # TODO: Move this to a helper function
        if section_content is None: # No data for this check type
            return False

        # In case of SNMP checks but missing agent response, skip this check.
        # Special checks which still need to be called even with empty data
        # may declare this.
        if not section_content and cmk_base.check_utils.is_snmp_check(check_plugin_name) \
           and not config.check_info[check_plugin_name]["handle_empty_info"]:
            return False

        check_function = config.check_info[check_plugin_name].get("check_function")
        if check_function is None:
            check_function = lambda item, params, section_content: (3, 'UNKNOWN - Check not implemented')

        # Call the actual check function
        item_state.reset_wrapped_counters()

        raw_result = check_function(item, _determine_check_params(params), section_content)
        result = sanitize_check_result(raw_result, cmk_base.check_utils.is_snmp_check(check_plugin_name))

        item_state.raise_counter_wrap()

    except item_state.MKCounterWrapped, e:
        # handle check implementations that do not yet support the
        # handling of wrapped counters via exception on their own.
        # Do not submit any check result in that case:
        console.verbose("%-20s PEND - Cannot compute check result: %s\n" % (description, e))
        dont_submit = True

    except MKTimeout:
        raise

    except Exception, e:
        if cmk.debug.enabled():
            raise
        result = 3, cmk_base.crash_reporting.create_crash_dump(hostname, check_plugin_name, item,
                                    is_manual_check(hostname, check_plugin_name, item),
                                    params, description, section_content), []

    if not dont_submit:
        # Now add information about the age of the data in the agent
        # sections. This is in data_sources.g_agent_cache_info. For clusters we
        # use the oldest of the timestamps, of course.
        oldest_cached_at = None
        largest_interval = None

        def minn(a, b):
            if a == None:
                return b
            elif b == None:
                return a
            return min(a,b)

        for host_sections in multi_host_sections.get_host_sections().values():
            section_entries = host_sections.cache_info
            if section_name in section_entries:
                cached_at, cache_interval = section_entries[section_name]
                oldest_cached_at = minn(oldest_cached_at, cached_at)
                largest_interval = max(largest_interval, cache_interval)

        _submit_check_result(hostname, description, result,
                            cached_at=oldest_cached_at, cache_interval=largest_interval)
    return True


def _determine_check_params(params):
    if isinstance(params, dict) and "tp_default_value" in params:
        for timeperiod, tp_params in params["tp_values"]:
            try:
                tp_result = cmk_base.core.timeperiod_active(timeperiod)
            except:
                if cmk.debug.enabled():
                    raise
                tp_result = None

            if tp_result == True:
                return tp_params
            elif tp_result == False:
                continue
            elif tp_result == None:
                # Connection error
                return params["tp_default_value"]
        return params["tp_default_value"]
    else:
        return params


def is_manual_check(hostname, check_plugin_name, item):
    manual_checks = check_table.get_check_table(hostname, remove_duplicates=True,
                                    world="active" if _in_keepalive_mode() else "config",
                                    skip_autochecks=True)
    return (check_plugin_name, item) in manual_checks


def sanitize_check_result(result, is_snmp):
    if type(result) == tuple:
        return _sanitize_tuple_check_result(result)

    elif result == None:
        return _item_not_found(is_snmp)

    else:
        return _sanitize_yield_check_result(result, is_snmp)


# The check function may return an iterator (using yield) since 1.2.5i5.
# This function handles this case and converts them to tuple results
def _sanitize_yield_check_result(result, is_snmp):
    subresults = list(result)

    # Empty list? Check returned nothing
    if not subresults:
        return _item_not_found(is_snmp)

    # Simple check with no separate subchecks (yield wouldn't have been neccessary here!)
    if len(subresults) == 1:
        state, infotext, perfdata = _sanitize_tuple_check_result(subresults[0], allow_missing_infotext=True)
        # just to be safe - infotext should allways be a string
        if infotext == None:
            return state, u"", perfdata
        else:
            return state, infotext, perfdata

    # Several sub results issued with multiple yields. Make that worst sub check
    # decide the total state, join the texts and performance data. Subresults with
    # an infotext of None are used for adding performance data.
    else:
        perfdata = []
        infotexts = []
        status = 0

        for subresult in subresults:
            st, text, perf = _sanitize_tuple_check_result(subresult, allow_missing_infotext=True)

            infotexts.append(text + ["", "(!)", "(!!)", "(?)"][st])
            status = cmk_base.utils.worst_service_state(st, status)

            if perf != None:
                perfdata += subresult[2]

        return status, ", ".join(i for i in infotexts if i), perfdata


def _item_not_found(is_snmp):
    if is_snmp:
        return 3, "Item not found in SNMP data", []
    else:
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
    if infotext == None and not allow_missing_infotext:
        raise MKGeneralException("Invalid infotext from check: \"None\"")

    if type(infotext) == str:
        return infotext.decode('utf-8')
    else:
        return infotext


def _convert_perf_data(p):
    # replace None with "" and fill up to 7 values
    p = (map(_convert_perf_value, p) + ['','','',''])[0:6]
    return "%s=%s;%s;%s;%s;%s" %  tuple(p)


def _convert_perf_value(x):
    if x == None:
        return ""
    elif type(x) in [ str, unicode ]:
        return x
    elif type(x) == float:
        return ("%.6f" % x).rstrip("0").rstrip(".")
    else:
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
        raise MKGeneralException("Invalid check result: %s" % (result, ))
    state, infotext, perfdata = result

    if not (
        infotext.startswith("OK -") or
        infotext.startswith("WARN -") or
        infotext.startswith("CRIT -") or
        infotext.startswith("UNKNOWN -")):
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
        if len(perfdata) > 0 and type(perfdata[-1]) in (str, unicode):
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

    console.verbose("%-20s %s%s"+infotext_fmt+"%s%s\n",
        servicedesc.encode('utf-8'), tty.bold, tty.states[state],
        cmk_base.utils.make_utf8(infotext.split('\n')[0]),
        tty.normal, cmk_base.utils.make_utf8(p))


def _do_submit_to_core(host, service, state, output, cached_at = None, cache_interval = None):
    if _in_keepalive_mode():
        # Regular case for the CMC - check helpers are running in keepalive mode
        keepalive.add_keepalive_check_result(host, service, state, output, cached_at, cache_interval)

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
        os.write(_checkresult_file_fd,
                """host_name=%s
service_description=%s
check_type=1
check_options=0
reschedule_check
latency=0.0
start_time=%.1f
finish_time=%.1f
return_code=%d
output=%s

""" % (host, cmk_base.utils.make_utf8(service), now, now,
       state, cmk_base.utils.make_utf8(output)))


def _open_checkresult_file():
    global _checkresult_file_fd
    global _checkresult_file_path
    if _checkresult_file_fd == None:
        try:
            _checkresult_file_fd, _checkresult_file_path = \
                tempfile.mkstemp('', 'c', cmk.paths.check_result_path)
        except Exception, e:
            raise MKGeneralException("Cannot create check result file in %s: %s" %
                    (cmk.paths.check_result_path, e))


def _close_checkresult_file():
    global _checkresult_file_fd
    if _checkresult_file_fd != None:
        os.close(_checkresult_file_fd)
        file(_checkresult_file_path + ".ok", "w")
        _checkresult_file_fd = None


def _submit_via_command_pipe(host, service, state, output):
    output = output.replace("\n", "\\n")
    _open_command_pipe()
    if _nagios_command_pipe:
        # [<timestamp>] PROCESS_SERVICE_CHECK_RESULT;<host_name>;<svc_description>;<return_code>;<plugin_output>
        _nagios_command_pipe.write("[%d] PROCESS_SERVICE_CHECK_RESULT;%s;%s;%d;%s\n" %
                               (int(time.time()), host,
                                cmk_base.utils.make_utf8(service),
                                state,
                                cmk_base.utils.make_utf8(output)))
        # Important: Nagios needs the complete command in one single write() block!
        # Python buffers and sends chunks of 4096 bytes, if we do not flush.
        _nagios_command_pipe.flush()


def _open_command_pipe():
    global _nagios_command_pipe
    if _nagios_command_pipe == None:
        if not os.path.exists(cmk.paths.nagios_command_pipe_path):
            _nagios_command_pipe = False # False means: tried but failed to open
            raise MKGeneralException("Missing core command pipe '%s'" % cmk.paths.nagios_command_pipe_path)
        else:
            try:
                signal.signal(signal.SIGALRM, _core_pipe_open_timeout)
                signal.alarm(3) # three seconds to open pipe
                _nagios_command_pipe =  file(cmk.paths.nagios_command_pipe_path, 'w')
                signal.alarm(0) # cancel alarm
            except Exception, e:
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
    else:
        return False
