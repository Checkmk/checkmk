#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import (
    Any,
    Dict,
    Generator,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import collections
import contextlib
import re
import time

from ..agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    HostLabelGenerator,
)
from ..agent_based_api.v1 import (
    check_levels,
    get_average,
    get_rate,
    get_value_store,
    HostLabel,
    IgnoreResultsError,
    Metric,
    regex,
    render,
    Result,
    Service,
    State as state,
)

from . import cpu, memory

ps_info = collections.namedtuple(
    "ps_info",
    (
        'user',
        'virtual',
        'physical',
        'cputime',
        'process_id',
        'pagefile',
        'usermode_time',
        'kernelmode_time',
        'handles',
        'threads',
        'uptime',
        'cgroup',
    ),
)

ps_info.__new__.__defaults__ = (None,) * len(ps_info._fields)  # type: ignore[attr-defined]

Section = Tuple[int, Sequence[Tuple[ps_info, Sequence[str]]]]


def get_discovery_specs(params: Sequence[Mapping[str, Any]]):
    inventory_specs = []
    for value in params[:-1]:  # skip empty default parameters
        inventory_specs.append((
            value['descr'],
            value.get('match'),
            value.get('user'),
            value.get('cgroup', (None, False)),
            value.get('label', {}),
            value['default_params'],
        ))
    return inventory_specs


def host_labels_ps(
    params: Sequence[Mapping[str, Any]],
    section: Section,
) -> HostLabelGenerator:
    specs = get_discovery_specs(params)
    for process_info, command_line in section[1]:
        for _servicedesc, pattern, userspec, cgroupspec, labels, _default_params in specs:
            # First entry in line is the node name or None for non-clusters
            if not process_attributes_match(process_info, userspec, cgroupspec):
                continue
            matches = process_matches(command_line, pattern)
            if not matches:
                continue  # skip not matched lines
            yield from (HostLabel(*item) for item in labels.items())


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


def process_matches(command_line: Sequence[str], process_pattern, match_groups=None):

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


def cpu_rate(value_store, counter, now, lifetime):
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
        self.max_elapsed: Optional[float] = None
        self.min_elapsed: Optional[float] = None
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

        if any((
                # Rule not set up, only windows scaled
                cpu_rescale_max == 'cpu_rescale_max_unspecified' and not is_win,
                # Current rule is set. Explicitly ask not to divide
                cpu_rescale_max is False,
                # Domino tasks counter
                cpu_rescale_max is None,
        )):
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

    def cpu_usage(self, value_store, process_info, process):

        now = time.time()

        pcpu_text = process_info.cputime.split('/')[0]

        if ":" in pcpu_text:  # In linux is a time
            total_seconds = parse_ps_time(pcpu_text)
            pid = process_info.process_id
            cputime = cpu_rate(value_store, "stat.pcpu.%s" % pid, now, total_seconds)

            pcpu = cputime * 100 * self.core_weight(is_win=False)
            process.append(("pid", (pid, "")))

        # windows cpu times
        elif process_info.usermode_time and process_info.kernelmode_time:
            pid = process_info.process_id

            user_per_sec = cpu_rate(value_store, "user.%s" % pid, now,
                                    int(process_info.usermode_time))
            kernel_per_sec = cpu_rate(value_store, "kernel.%s" % pid, now,
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


def process_capture(
    # process_lines: (Node, PsInfo, cmd_line)
    process_lines: Iterable[Tuple[Optional[str], ps_info, Sequence[str]]],
    params: Mapping[str, Any],
    cpu_cores: int,
    value_store: MutableMapping[str, Any],
) -> ProcessAggregator:

    ps_aggregator = ProcessAggregator(cpu_cores, params)

    userspec = params.get("user")
    cgroupspec = params.get("cgroup", (None, False))

    for node_name, process_info, command_line in process_lines:

        if not process_attributes_match(process_info, userspec, cgroupspec):
            continue

        if not process_matches(command_line, params.get("process"), params.get('match_groups')):
            continue

        # typing: nothing intentional, just adapt to sad reality
        process: List[Tuple[str, Tuple[Union[str, float], str]]] = []

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
            ps_aggregator.cpu_usage(value_store, process_info, process)

        include_args = params.get("process_info_arguments", 0)
        if include_args:
            process.append(("args", (' '.join(command_line[1:])[:include_args], "")))

        ps_aggregator.append(process)

    return ps_aggregator


def discover_ps(
    params: Sequence[Mapping[str, Any]],
    section_ps: Optional[Section],
    section_mem: Optional[memory.SectionMem],
    section_mem_used: Optional[Dict[str, memory.SectionMem]],
    section_cpu: Optional[cpu.Section],
) -> DiscoveryResult:
    if not section_ps:
        return

    inventory_specs = get_discovery_specs(params)

    for process_info, command_line in section_ps[1]:
        for servicedesc, pattern, userspec, cgroupspec, _labels, default_params in inventory_specs:
            if not process_attributes_match(process_info, userspec, cgroupspec):
                continue
            matches = process_matches(command_line, pattern)
            if not matches:
                continue  # skip not matched lines

            # User capturing on rule
            if userspec is False:
                i_userspec = process_info.user
            else:
                i_userspec = userspec

            i_servicedesc = servicedesc.replace("%u", i_userspec or "")

            # Process capture
            match_groups = matches.groups() if hasattr(matches, 'groups') else ()

            i_servicedesc = replace_service_description(i_servicedesc, match_groups, pattern)

            # Problem here: We need to instantiate all subexpressions
            # with their actual values of the found process.
            inv_params = {
                "process": pattern,
                "match_groups": match_groups,
                "user": i_userspec,
                "cgroup": cgroupspec,
                **default_params,
            }

            yield Service(
                item=i_servicedesc,
                parameters=inv_params,
            )


@contextlib.contextmanager
def unused_value_remover(
    value_store: MutableMapping[str, Any],
    key: str,
) -> Generator[Dict[str, Tuple[float, float]], None, None]:
    """Remove all values that remain unchanged

    This plugin uses the process IDs in the keys to persist values.
    This would lead to a lot of orphaned values if we used the value store directly.
    Thus we use a single dictionary and only store the values that have been used.
    """
    values = value_store.setdefault(key, {})
    old_values = values.copy()

    yield values

    value_store[key] = {k: v for k, v in values.items() if v != old_values.get(k)}


def check_ps_common(
    *,
    label: str,
    item: str,
    params: Mapping[str, Any],
    process_lines: Iterable[Tuple[Optional[str], ps_info, Sequence[str]]],
    cpu_cores: int,
    total_ram_map: Mapping[str, float],
) -> CheckResult:
    with unused_value_remover(get_value_store(), "collective") as value_store:
        processes = process_capture(process_lines, params, cpu_cores, value_store)

    yield from count_check(processes, params, label)

    yield from memory_check(processes, params)

    yield from memory_perc_check(processes, params, total_ram_map)

    # CPU
    if processes.count:
        yield from cpu_check(processes.percent_cpu, params)

    if "single_cpulevels" in params:
        yield from individual_process_check(processes, params)

    # only check handle_count if provided by wmic counters
    if processes.handle_count:
        yield from handle_count_check(processes, params)

    if processes.min_elapsed is not None and processes.max_elapsed is not None:
        yield from uptime_check(processes.min_elapsed, processes.max_elapsed, params)

    if processes.count and params.get("process_info") is not None:
        yield Result(
            state=state.OK,
            notice=format_process_list(processes, params["process_info"] == "html"),
        )


def count_check(
    processes: ProcessAggregator,
    params: Mapping[str, Any],
    info_name: str,
) -> CheckResult:
    warnmin, okmin, okmax, warnmax = params["levels"]
    yield from check_levels(
        processes.count,
        metric_name="count",
        levels_lower=(okmin, warnmin),
        levels_upper=(okmax + 1, warnmax + 1),
        render_func=lambda d: str(int(d)),
        boundaries=(0, None),
        label=info_name,
    )
    if processes.running_on_nodes:
        yield Result(
            state=state.OK,
            summary="Running on nodes %s" % ", ".join(sorted(processes.running_on_nodes)),
        )


def memory_check(
    processes: ProcessAggregator,
    params: Mapping[str, Any],
) -> CheckResult:
    """Check levels for virtual and physical used memory"""
    for size, label, levels, metric in [
        (processes.virtual_size, "virtual", "virtual_levels", "vsz"),
        (processes.resident_size, "physical", "resident_levels", "rss"),
    ]:
        if size == 0:
            continue

        yield from check_levels(
            size * 1024,
            levels_upper=params.get(levels),
            render_func=render.bytes,
            label=label,
        )
        yield Metric(metric, size, levels=params.get(levels))


def memory_perc_check(
    processes: ProcessAggregator,
    params: Mapping[str, Any],
    total_ram_map: Mapping[str, float],
) -> CheckResult:
    """Check levels that are in percent of the total RAM of the host"""
    if not processes.resident_size or "resident_levels_perc" not in params:
        return

    nodes = processes.running_on_nodes or ("",)

    try:
        total_ram = sum(total_ram_map[node] for node in nodes)
    except KeyError:
        yield Result(
            state=state.UNKNOWN,
            summary="Percentual RAM levels configured, but total RAM is unknown",
        )
        return

    resident_perc = 100.0 * processes.resident_size * 1024.0 / total_ram
    yield from check_levels(
        resident_perc,
        levels_upper=params["resident_levels_perc"],
        render_func=render.percent,
        label="Percentage of total RAM",
    )


def cpu_check(percent_cpu: float, params: Mapping[str, Any]) -> CheckResult:
    """Check levels for cpu utilization from given process"""

    warn_cpu, crit_cpu = params.get("cpulevels", (None, None, None))[:2]
    yield Metric("pcpu", percent_cpu, levels=(warn_cpu, crit_cpu))

    # CPU might come with previous
    if "cpu_average" in params:
        avg_cpu = get_average(
            get_value_store(),
            "cpu",
            time.time(),
            percent_cpu,
            params["cpu_average"],
        )
        infotext = "CPU: %s, %d min average" % (render.percent(percent_cpu), params["cpu_average"])
        yield Metric("pcpuavg",
                     avg_cpu,
                     levels=(warn_cpu, crit_cpu),
                     boundaries=(0, params["cpu_average"]))  # wat?
        percent_cpu = avg_cpu  # use this for level comparison
    else:
        infotext = "CPU"

    yield from check_levels(
        percent_cpu,
        levels_upper=(warn_cpu, crit_cpu),
        render_func=render.percent,
        label=infotext,
    )


def individual_process_check(
    processes: ProcessAggregator,
    params: Mapping[str, Any],
) -> CheckResult:
    levels = params["single_cpulevels"]
    for p in processes.processes:
        cpu_usage, name, pid = 0.0, None, None

        for the_item, (value, _unit) in p:
            if the_item == "name":
                name = value
            if the_item == "pid":
                pid = value
            elif the_item.startswith("cpu usage"):
                cpu_usage += value

        result, *_ = check_levels(
            cpu_usage,
            levels_upper=levels,
            render_func=render.percent,
            label=str(name) + (" with PID %s CPU" % pid if pid else ""),
        )
        # To avoid listing of all processes regardless of level setting we
        # only generate output in case WARN level has been reached.
        # In case a full list of processes is desired, one should enable
        # `process_info`, i.E."Enable per-process details in long-output"
        if result.state is not state.OK:
            yield Result(
                state=result.state,
                notice=result.summary,
            )


def uptime_check(
    min_elapsed: float,
    max_elapsed: float,
    params: Mapping[str, Any],
) -> CheckResult:
    """Check how long the process is running"""
    if min_elapsed == max_elapsed:
        yield from check_levels(
            min_elapsed,
            levels_lower=params.get("min_age"),
            levels_upper=params.get("max_age"),
            render_func=render.timespan,
            label="Running for",
        )
    else:
        yield from check_levels(
            min_elapsed,
            levels_lower=params.get("min_age"),
            render_func=render.timespan,
            label="Youngest running for",
        )
        yield from check_levels(
            max_elapsed,
            levels_upper=params.get("max_age"),
            render_func=render.timespan,
            label="Oldest running for",
        )


def handle_count_check(
    processes: ProcessAggregator,
    params: Mapping[str, Any],
) -> CheckResult:
    yield from check_levels(
        processes.handle_count,
        metric_name="process_handles",
        levels_upper=params.get("handle_count"),
        render_func=lambda d: str(int(d)),
        label="Process handles",
    )
