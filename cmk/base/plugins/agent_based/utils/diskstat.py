#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict
import re
import time
from typing import (
    Callable,
    DefaultDict,
    Iterable,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
)
from ..agent_based_api.v1 import (
    check_levels,
    get_average,
    IgnoreResultsError,
    Metric,
    render,
    Service,
    type_defs,
)

Disk = Mapping[str, float]
Section = Mapping[str, Disk]

DISKSTAT_DISKLESS_PATTERN = re.compile("x?[shv]d[a-z]*[0-9]+")


def discovery_diskstat_generic(
    params: Sequence[type_defs.Parameters],
    section: Section,
) -> type_defs.DiscoveryResult:
    # Skip over on empty data
    if not section:
        return

    modes = params[0]

    if "summary" in modes:
        yield Service(item="SUMMARY")

    for name in section:
        if "physical" in modes and ' ' not in name and not DISKSTAT_DISKLESS_PATTERN.match(name):
            yield Service(item=name)

        if "lvm" in modes and name.startswith("LVM "):
            yield Service(item=name)

        if "vxvm" in modes and name.startswith("VxVM "):
            yield Service(item=name)

        if "diskless" in modes and DISKSTAT_DISKLESS_PATTERN.match(name):
            # Sort of partitions with disks - typical in XEN virtual setups.
            # Eg. there are xvda1, xvda2, but no xvda...
            yield Service(item=name)


def compute_rates_multiple_disks(
    disks: Section,
    value_store: type_defs.ValueStore,
    single_disk_rate_computer: Callable[[Disk, type_defs.ValueStore, str], Disk],
) -> Section:
    disks_with_rates = {}
    ignore_res_excpt = None

    for disk_name, disk in disks.items():
        try:
            disks_with_rates[disk_name] = single_disk_rate_computer(
                disk,
                value_store,
                '.%s' % disk_name,
            )
        except IgnoreResultsError as excpt:
            ignore_res_excpt = excpt

    if ignore_res_excpt:
        raise ignore_res_excpt

    return disks_with_rates


def combine_disks(disks: Iterable[Disk]) -> Disk:

    # In summary mode we add up the throughput values, but
    # we average the other values for disks that have a throughput
    # > 0. Note: This is not very precise. Strictly spoken
    # we would need to do the summarization directly in the
    # parse function. But there we do not have information about
    # the physical multipath devices and would add up the traffic
    # of the paths with the traffice of the device itself....

    combined_disk: DefaultDict[str, float] = defaultdict(float)
    # We do not set these settings explictly because some
    # devices may not provide all of them.
    # "read_ios"                   : 0.0,
    # "write_ios"                  : 0.0,
    # "read_throughput"            : 0.0,
    # "write_throughput"           : 0.0,
    # "utilization"                : 0.0,
    # "latency"                    : 0.0,
    # "average_request_size"       : 0.0,
    # "average_wait"               : 0.0,
    # "average_read_wait"          : 0.0,
    # "average_read_request_size"  : 0.0,
    # "average_write_wait"         : 0.0,
    # "average_write_request_size" : 0.0,
    # "queue_length"               : 0.0,
    # "read_ql"                    : 0.0,
    # "write_ql"                   : 0.0,
    n_contributions: DefaultDict[str, int] = defaultdict(int)

    for disk in disks:
        for key, value in disk.items():
            combined_disk[key] += value
            n_contributions[key] += 1

    for key in combined_disk:
        if key.startswith("ave") or key in ("utilization", "latency", "queue_length"):
            combined_disk[key] /= n_contributions[key]

    return combined_disk


def summarize_disks(disks: Iterable[Tuple[str, Disk]]) -> Disk:
    # we do not use a dictionary as input because we want to be able to have the same disk name
    # multiple times (cluster mode)
    # skip LVM devices for summary
    return combine_disks(disk for device, disk in disks if not device.startswith("LVM "))


def _scale_levels(
    levels: Optional[Tuple[float, float]],
    factor: Union[int, float],
) -> Optional[Tuple[float, float]]:
    if levels is None:
        return None
    return (levels[0] * factor, levels[1] * factor)


class MetricSpecs(TypedDict, total=False):
    value_scale: float
    levels_key: str
    levels_scale: float
    render_func: Callable[[float], str]
    label: str


_METRICS: Mapping[str, MetricSpecs] = {
    'utilization': {
        'levels_scale': 0.01,  # value comes as fraction, but levels are specified in percent
        'render_func': lambda x: render.percent(x * 100),
    },
    'read_throughput': {
        'levels_key': 'read',
        'levels_scale': 1e6,  # levels are specified in MB/s
        'render_func': render.iobandwidth,
    },
    'write_throughput': {
        'levels_key': 'write',
        'levels_scale': 1e6,  # levels are specified in MB/s
        'render_func': render.iobandwidth,
    },
    'average_wait': {
        'levels_scale': 1e-3,  # levels are specified in ms
        'render_func': render.timespan,
    },
    'average_read_wait': {
        'levels_key': 'read_wait',
        'levels_scale': 1e-3,  # levels are specified in ms
        'render_func': render.timespan,
    },
    'average_write_wait': {
        'levels_key': 'write_wait',
        'levels_scale': 1e-3,  # levels are specified in ms
        'render_func': render.timespan,
    },
    'latency': {
        'levels_scale': 1e-3,  # levels are specified in ms
        'render_func': render.timespan,
    },
    'read_latency': {
        'levels_scale': 1e-3,  # levels are specified in ms
        'render_func': render.timespan,
    },
    'write_latency': {
        'levels_scale': 1e-3,  # levels are specified in ms
        'render_func': render.timespan,
    },
    'queue_length': {
        'render_func': lambda x: "%.2f" % x,
        'label': 'Average queue length',
    },
    'read_ql': {
        'render_func': lambda x: "%.2f" % x,
        'label': 'Average read queue length',
    },
    'write_ql': {
        'render_func': lambda x: "%.2f" % x,
        'label': 'Average write queue length',
    },
    'read_ios': {
        'render_func': lambda x: "%.2f/s" % x,
        'label': 'Read operations',
    },
    'write_ios': {
        'render_func': lambda x: "%.2f/s" % x,
        'label': 'Write operations',
    },
}


# Example:
# disks = { "sda" : {
#       'average_read_request_size'  : 0.0,
#       'average_read_wait'          : 0.0,
#       'average_request_size'       : 40569.90476190476,
#       'average_wait'               : 0.761904761904762,
#       'average_write_request_size' : 40569.90476190476,
#       'average_write_wait'         : 0.0007619047619047619,
#       'read_ios'                   : 0.0,
#       'read_throughput'            : 0.0,
#       'latency'                    : 0.00038095238095238096,
#       'utilization'                : 0.0006153846153846154,
#       'write_ios'                  : 1.6153846153846154,
#       'write_throughput'           : 65536.0,
#       'queue_length'               : 0.0,
#       'read_ql'                    : 0.0,
#       'write_ql'                   : 0.0,
# }}
def check_diskstat_dict(
    params: type_defs.Parameters,
    disk: Disk,
    value_store,
) -> type_defs.CheckResult:
    # Averaging
    # Note: this check uses a simple method of averaging: As soon as averaging
    # is turned on the actual metrics are *replaced* by the averaged ones. No
    # duplication of performance data or check output here. This is because we
    # have so many metrics...
    prefix = ""
    # here, a value in seconds must be provided (preferably from the ruleset "diskstat"); note that
    # the deprecated ruleset "disk_io" uses minutes for this field and is therefore incompatible
    # with this function
    averaging = params.get("average")
    if averaging:
        avg_disk = {}  # Do not modify our arguments!!
        for key, value in disk.items():
            if isinstance(value, (int, float)):
                avg_disk[key] = get_average(
                    value_store=value_store,
                    # We add 'check_diskstat_dict' to the key to avoid possible overlap with keys
                    # used in check plugins. For example, for the SUMMARY-item, the check plugin
                    # winperf_phydisk first computes all rates for all items using 'metric.item' as
                    # key and then summarizes the disks. Hence, for a disk called 'avg', these keys
                    # would be the same as the keys used here.
                    key="check_diskstat_dict.%s.avg" % key,
                    time=time.time(),
                    value=value,
                    backlog_minutes=averaging / 60.,
                )
            else:
                avg_disk[key] = value
        disk = avg_disk
        prefix = "%s average: " % render.timespan(averaging)

    for key, specs in _METRICS.items():
        metric_val = disk.get(key)
        if metric_val is not None:
            yield from check_levels(
                metric_val,
                levels_upper=_scale_levels(
                    params.get(specs.get('levels_key') or key),
                    specs.get('levels_scale', 1),
                ),
                metric_name="disk_" + key,
                render_func=specs.get('render_func'),
                label=prefix + (specs.get('label') or key.replace("_", " ").capitalize()),
            )
            prefix = ''

    # All the other metrics are currently not output in the plugin output - simply because
    # of their amount. They are present as performance data and will shown in graphs.

    # Send everything as performance data now. Sort keys alphabetically
    for key in sorted(set(disk) - set(_METRICS)):
        value = disk[key]
        if isinstance(value, (int, float)):
            # Currently the levels are not shown in the perfdata
            yield Metric("disk_" + key, value)
