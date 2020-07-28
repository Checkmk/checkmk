#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections
import re

from ..agent_based_api.v0 import get_rate, get_value_store, IgnoreResultsError, regex

ps_info = collections.namedtuple(
    "Process_Info", ('user', 'virtual', 'physical', 'cputime', 'process_id', 'pagefile',
                     'usermode_time', 'kernelmode_time', 'handles', 'threads', 'uptime', 'cgroup'))

ps_info.__new__.__defaults__ = (None,) * len(ps_info._fields)  # type: ignore[attr-defined]


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


# Parse time as output by ps into seconds.
# Example 1: "12:17"
# Example 2: "55:12:17"
# Example 3: "7-12:34:59" (with 7 days)
# Example 4: "7123459" (only seconds, windows)
def parse_ps_time(text):
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
