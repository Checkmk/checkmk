#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Tuple

import collections
import re
import time

from ..agent_based_api.v0.type_defs import HostLabelGenerator, Parameters
from ..agent_based_api.v0 import (
    get_rate,
    get_value_store,
    IgnoreResultsError,
    regex,
    render,
)

ps_info = collections.namedtuple(
    "Process_Info", ('user', 'virtual', 'physical', 'cputime', 'process_id', 'pagefile',
                     'usermode_time', 'kernelmode_time', 'handles', 'threads', 'uptime', 'cgroup'))

ps_info.__new__.__defaults__ = (None,) * len(ps_info._fields)  # type: ignore[attr-defined]


def get_discovery_specs(params):
    inventory_specs = []
    for value in params:
        default_params = value.get('default_params', value)
        if "cpu_rescale_max" not in default_params:
            default_params["cpu_rescale_max"] = None

        inventory_specs.append((
            value['descr'],
            value.get('match'),
            value.get('user'),
            value.get('cgroup', (None, False)),
            value.get('label', {}),
            default_params,
        ))

    return inventory_specs


def host_labels_ps(
    params: List[Parameters],
    section: Tuple[int, List],
) -> HostLabelGenerator:
    specs = get_discovery_specs(params)
    for process_info, *command_line in section[1]:
        for _servicedesc, pattern, userspec, cgroupspec, labels, _default_params in specs:
            # First entry in line is the node name or None for non-clusters
            if not process_attributes_match(process_info, userspec, cgroupspec):
                continue
            matches = process_matches(command_line, pattern)
            if not matches:
                continue  # skip not matched lines

            yield from labels.values()


def minn(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


def maxx(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


def ps_info_tuple(entry):
    ps_tuple_re = regex(r"^\((.*)\)$")
    matched_ps_info = ps_tuple_re.match(entry)
    if matched_ps_info:
        return ps_info(*matched_ps_info.group(1).split(","))
    return False


def replace_service_description(service_description, match_groups, pattern):

    # New in 1.2.2b4: All %1, %2, etc. to be replaced with first, second, ...
    # group. This allows a reordering of the matched groups
    # replace all %1:
    description_template, count = re.subn(r'%(\d+)', r'{\1}', service_description)
    # replace plain %s:
    total_replacements_count = count + description_template.count('%s')
    for number in range(count + 1, total_replacements_count + 1):
        description_template = description_template.replace('%s', '{%d}' % number, 1)

    # It is allowed (1.1.4) that the pattern contains more subexpressions
    # then the service description. In that case only the first
    # subexpressions are used as item.
    try:
        # First argument is None, because format is zero indexed
        return description_template.format(None, *(g or "" for g in match_groups))
    except IndexError:
        raise ValueError(
            "Invalid entry in inventory_processes_rules: service description '%s' contains %d "
            "replaceable elements, but regular expression %r contains only %d subexpression(s)." %
            (service_description, total_replacements_count, pattern, len(match_groups)))


def match_attribute(attribute, pattern):
    if not pattern:
        return True

    if pattern.startswith('~'):
        return bool(regex(pattern[1:]).match(attribute))

    return pattern == attribute


def process_attributes_match(process_info, userspec, cgroupspec):

    cgroup_pattern, invert = cgroupspec
    if process_info.cgroup and (match_attribute(process_info.cgroup, cgroup_pattern) is invert):
        return False

    if not match_attribute(process_info.user, userspec):
        return False

    return True


def process_matches(command_line, process_pattern, match_groups=None):

    if not process_pattern:
        # Process name not relevant
        return True

    if process_pattern.startswith("~"):
        # Regex for complete process command line
        reg = regex(process_pattern[1:])  # skip "~"
        m = reg.match(" ".join(command_line))
        if not m:
            return False
        if match_groups:
            # Versions prior to 1.5.0p20 discovered a list, so keep tuple conversion!
            return m.groups() == tuple(match_groups)
        return m

    # Exact match on name of executable
    return command_line[0] == process_pattern


# produce text or html output intended for the long output field of a check
# from details about a process.  the input is expected to be a list (one
# per process) of lists (one per data field) of key-value tuples where the
# value is again a 2-field tuple, first is the value, second is the unit.
# This function is actually fairly generic so it could be used for other
# data structured the same way
def format_process_list(processes, html_output):
    def format_value(value):
        value, unit = value
        if isinstance(value, float):
            return "%.1f%s" % (value, unit)
        return "%s%s" % (value, unit)

    if html_output:
        table_bracket = "<table>%s</table>"
        line_bracket = "<tr>%s</tr>"
        cell_bracket = "<td>%.0s%s</td>"
        cell_seperator = ""

        headers = []
        headers_found = set()

        for process in processes:
            for key, _value in process:
                if key not in headers_found:
                    headers.append(key)
                    headers_found.add(key)

        # make sure each process has all fields from the table
        processes_filled = []
        for process in processes:
            dictified = dict(process)
            processes_filled.append([(key, dictified.get(key, "")) for key in headers])
        processes = processes_filled
        header_line = "<tr><th>" + "</th><th>".join(headers) + "</th></tr>"
    else:
        table_bracket = "%s"
        line_bracket = "%s\r\n"
        cell_bracket = "%s %s"
        cell_seperator = ", "
        header_line = ""

    return table_bracket % (header_line + "".join([
        line_bracket %
        cell_seperator.join([cell_bracket % (key, format_value(value))
                             for key, value in process])
        for process in processes
    ]))


def parse_ps_time(text):
    """Parse time as output by ps into seconds

        >>> parse_ps_time("12:17")
        737
        >>> parse_ps_time("55:12:17")
        198737
        >>> parse_ps_time("7-12:34:59")
        650099
        >>> parse_ps_time("650099")
        650099

    """
    if "-" in text:
        tokens = text.split("-")
        days = int(tokens[0] or 0)
        text = tokens[1]
    else:
        days = 0

    day_secs = sum(
        [factor * int(v or 0) for factor, v in zip([1, 60, 3600], reversed(text.split(":")))])

    return 86400 * days + day_secs


# This function is repeated in cmk/gui/plugins/wato/check_parameters/ps.py
# Update that function too until we can import them
def ps_cleanup_params(params):
    # New parameter format: dictionary. Example:
    # {
    #    "user" : "foo",
    #    "process" : "/usr/bin/food",
    #    "warnmin" : 1,
    #    "okmin"   : 1,
    #    "okmax"   : 1,
    #    "warnmax" : 1,
    # }

    # Even newer format:
    # {
    #   "user" : "foo",
    #   "levels" : (1, 1, 99999, 99999)
    # }
    if isinstance(params, (list, tuple)):
        if len(params) == 5:
            procname, warnmin, okmin, okmax, warnmax = params
            user = None
        elif len(params) == 6:
            procname, user, warnmin, okmin, okmax, warnmax = params

        params = {
            "process": procname,
            "levels": (warnmin, okmin, okmax, warnmax),
            "user": user,
        }

    elif any(k in params for k in ['okmin', 'warnmin', 'okmax', 'warnmax']):
        params["levels"] = (
            params.pop("warnmin", 1),
            params.pop("okmin", 1),
            params.pop("okmax", 99999),
            params.pop("warnmax", 99999),
        )

    if "cpu_rescale_max" not in params:
        params["cpu_rescale_max"] = None

    return params


def cpu_rate(counter, now, lifetime):
    value_store = get_value_store()
    try:
        return get_rate(value_store, counter, now, lifetime)
    except IgnoreResultsError:
        return 0


class ProcessAggregator:
    """Collects information about all instances of monitored processes"""
    def __init__(self, cpu_cores, params):
        self.cpu_cores = cpu_cores
        self.params = params
        self.virtual_size = 0
        self.resident_size = 0
        self.handle_count = 0
        self.percent_cpu = 0.0
        self.max_elapsed = None
        self.min_elapsed = None
        self.processes = []
        self.running_on_nodes = set()

    def __getitem__(self, item):
        return self.processes[item]

    @property
    def count(self):
        return len(self.processes)

    def append(self, process):
        self.processes.append(process)

    def core_weight(self, is_win):
        cpu_rescale_max = self.params.get('cpu_rescale_max')

        # Rule not set up, only windows scaled
        if cpu_rescale_max is None and not is_win:
            return 1.0

        # Current rule is set. Explicitly ask not to divide
        if cpu_rescale_max is False:
            return 1.0

        # Use default of division
        return 1.0 / self.cpu_cores

    def lifetimes(self, process_info, process):
        # process_info.cputime contains the used CPU time and possibly,
        # separated by /, also the total elapsed time since the birth of the
        # process.
        if '/' in process_info.cputime:
            elapsed_text = process_info.cputime.split('/')[1]
        else:
            # uptime is a windows only value, introduced in Werk 4029. For
            # future consistency should be moved to the cputime entry and
            # separated by a /
            if process_info.uptime:
                elapsed_text = process_info.uptime
            else:
                elapsed_text = None

        if elapsed_text:
            elapsed = parse_ps_time(elapsed_text)
            self.min_elapsed = minn(self.min_elapsed or elapsed, elapsed)
            self.max_elapsed = maxx(self.max_elapsed, elapsed)

            now = time.time()
            creation_time_unix = int(now - elapsed)
            if creation_time_unix != 0:
                process.append((
                    "creation time",
                    (render.datetime(creation_time_unix), ""),
                ))

    def cpu_usage(self, process_info, process):

        now = time.time()

        pcpu_text = process_info.cputime.split('/')[0]

        if ":" in pcpu_text:  # In linux is a time
            total_seconds = parse_ps_time(pcpu_text)
            pid = process_info.process_id
            cputime = cpu_rate("ps_stat.pcpu.%s" % pid, now, total_seconds)

            pcpu = cputime * 100 * self.core_weight(is_win=False)
            process.append(("pid", (pid, "")))

        # windows cpu times
        elif process_info.usermode_time and process_info.kernelmode_time:
            pid = process_info.process_id

            user_per_sec = cpu_rate("ps_wmic.user.%s" % pid, now, int(process_info.usermode_time))
            kernel_per_sec = cpu_rate("ps_wmic.kernel.%s" % pid, now,
                                      int(process_info.kernelmode_time))

            if not all([user_per_sec, kernel_per_sec]):
                user_per_sec = 0
                kernel_per_sec = 0

            core_weight = self.core_weight(is_win=True)
            user_perc = user_per_sec / 100000.0 * core_weight
            kernel_perc = kernel_per_sec / 100000.0 * core_weight
            pcpu = user_perc + kernel_perc
            process.append(("cpu usage (user space)", (user_perc, "%")))
            process.append(("cpu usage (kernel space)", (kernel_perc, "%")))
            process.append(("pid", (pid, "")))

        else:  # Solaris, BSD, aix cpu times
            if pcpu_text == '-':  # Solaris defunct
                pcpu_text = 0.0
            pcpu = float(pcpu_text) * self.core_weight(is_win=False)

        self.percent_cpu += pcpu
        process.append(("cpu usage", (pcpu, "%")))

        if process_info.pagefile:
            process.append(("pagefile usage", (process_info.pagefile, "")))

        if process_info.handles:
            self.handle_count += int(process_info.handles)
            process.append(("handle count", (int(process_info.handles), "")))


def process_capture(parsed, params, cpu_cores):

    ps_aggregator = ProcessAggregator(cpu_cores, params)

    userspec = params.get("user")
    cgroupspec = params.get("cgroup", (None, False))

    for line in parsed:
        node_name, process_line = line[0], line[1:]
        process_info, command_line = process_line[0], process_line[1:]

        if not process_attributes_match(process_info, userspec, cgroupspec):
            continue

        if not process_matches(command_line, params.get("process"), params.get('match_groups')):
            continue

        process = []

        if node_name is not None:
            ps_aggregator.running_on_nodes.add(node_name)

        if command_line:
            process.append(("name", (command_line[0], "")))

        # extended performance data: virtualsize, residentsize, %cpu
        if all(process_info[1:4]):
            process.append(("user", (process_info.user, "")))
            process.append(("virtual size", (int(process_info.virtual), "kB")))
            process.append(("resident size", (int(process_info.physical), "kB")))

            ps_aggregator.virtual_size += int(process_info.virtual)  # kB
            ps_aggregator.resident_size += int(process_info.physical)  # kB

            ps_aggregator.lifetimes(process_info, process)
            ps_aggregator.cpu_usage(process_info, process)

        include_args = params.get("process_info_arguments", 0)
        if include_args:
            process.append(("args", (' '.join(command_line[1:])[:include_args], "")))

        ps_aggregator.append(process)

    return ps_aggregator
