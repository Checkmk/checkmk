#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# pylint: disable=consider-using-in

# pylint: disable=no-else-continue

# pylint: disable=no-else-return

import re
import time
from typing import (
    Any,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from cmk.base.check_api import (
    check_levels,
    get_age_human_readable,
    get_average,
    get_percent_human_readable,
    get_rate,
    host_extra_conf,
    host_name,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import render
from cmk.base.plugins.agent_based.utils.diskstat import _METRICS_TO_BE_AVERAGED

diskstat_inventory_mode = "rule"  # "summary", "single", "legacy"

diskstat_default_levels: Mapping[str, Any] = {
    #    "read" :    (10, 20),   # MB/sec
    #    "write" :   (20, 40),   # MB/sec
    #    "average" : 15,         # min
    #    "latency" : (10, 20),   # ms
    #    "latency_perfdata" : True,
}

# Rule for controlling diskstat inventory more fine grained
diskstat_inventory: Any = []

# Example
# diskstat_inventory = [
#  ( [], [ 'linux' ], ALL_HOST ), --> No diskstat on this host
#  ( [ 'summary', 'physical', 'lvm', 'vxvm' ], ALL_HOSTS ),
# ]

diskstat_diskless_pattern = re.compile("x?[shv]d[a-z]*[0-9]+")


# ==================================================================================================
# ==================================================================================================
# THIS FUNCTION HAS BEEN MIGRATED TO THE NEW CHECK API (OR IS IN THE PROCESS), PLEASE DO NOT TOUCH
# IT. INSTEAD, MODIFY THE MIGRATED VERSION.
# ==================================================================================================
# ==================================================================================================
def inventory_diskstat_generic(  # pylint: disable=too-many-branches
    parsed: Sequence[Sequence[Any]],
) -> Optional[Sequence[Tuple[str, Optional[str]]]]:
    # Skip over on empty data
    if not parsed:
        return None

    # New style: use rule based configuration, defaulting to summary mode
    if diskstat_inventory_mode == "rule":
        hits = host_extra_conf(host_name(), diskstat_inventory)
        if len(hits) > 0:
            modes = hits[0]
        else:
            modes = ["summary"]

    elif diskstat_inventory_mode == "single":
        modes = ["physical"]
    elif diskstat_inventory_mode == "summary":
        modes = ["summary"]
    else:
        modes = ["legacy"]

    inventory: MutableSequence[Tuple[str, Optional[str]]] = []
    if "summary" in modes:
        inventory.append(("SUMMARY", "diskstat_default_levels"))

    if "legacy" in modes:
        inventory += [("read", None), ("write", None)]

    for line in parsed:
        name = line[1]
        if "physical" in modes and not " " in name and not diskstat_diskless_pattern.match(name):
            inventory.append((name, "diskstat_default_levels"))

        if "lvm" in modes and name.startswith("LVM "):
            inventory.append((name, "diskstat_default_levels"))

        if "vxvm" in modes and name.startswith("VxVM "):
            inventory.append((name, "diskstat_default_levels"))

        if "diskless" in modes and diskstat_diskless_pattern.match(name):
            # Sort of partitions with disks - typical in XEN virtual setups.
            # Eg. there are xvda1, xvda2, but no xvda...
            inventory.append((name, "diskstat_default_levels"))

    return inventory


def check_diskstat_line(  # pylint: disable=too-many-branches
    this_time: float,
    item: str,
    params: Mapping[str, Any],
    line: Sequence[Any],
    mode: str = "sectors",
) -> Tuple[int, str, MutableSequence[Any],]:
    average_range = params.get("average")
    if average_range == 0:
        average_range = None  # disable averaging when 0 is set

    perfdata: MutableSequence[Any] = []
    infos: MutableSequence[str] = []
    status: int = 0
    node = line[0]
    if node is not None and node != "":
        infos.append("Node %s" % node)

    for what, ctr in [("read", line[2]), ("write", line[3])]:
        if node:
            countername = "diskstat.%s.%s.%s" % (node, item, what)
        else:
            countername = "diskstat.%s.%s" % (item, what)

        # unpack levels now, need also for perfdata
        levels = params.get(what)
        if isinstance(levels, tuple):
            warn, crit = levels
        else:
            warn, crit = None, None

        per_sec = get_rate(countername, this_time, int(ctr))
        if mode == "sectors":
            # compute IO rate in bytes/sec
            bytes_per_sec = per_sec * 512
        elif mode == "bytes":
            bytes_per_sec = per_sec

        dsname = what

        # compute average of the rate over ___ minutes
        if average_range is not None:
            perfdata.append((dsname, bytes_per_sec, warn, crit))
            bytes_per_sec = get_average(
                countername + ".avg", this_time, bytes_per_sec, average_range
            )
            dsname += ".avg"

        # check levels
        state, text, extraperf = check_levels(
            bytes_per_sec,
            dsname,
            levels,
            scale=1048576,
            statemarkers=True,
            human_readable_func=render.iobandwidth,
            infoname=what,
        )
        if text:
            infos.append(text)
        status = max(state, status)
        perfdata += extraperf

    # Add performance data for averaged IO
    if average_range is not None:
        perfdata = [perfdata[0], perfdata[2], perfdata[1], perfdata[3]]

    # Process IOs when available
    ios_per_sec = None
    if len(line) >= 6 and line[4] >= 0 and line[5] > 0:
        reads, writes = map(int, line[4:6])
        if "read_ios" in params:
            warn, crit = params["read_ios"]
            if reads >= crit:
                infos.append("Read operations: %d (!!)" % (reads))
                status = 2
            elif reads >= warn:
                infos.append("Read operations: %d (!)" % (reads))
                status = max(status, 1)
        else:
            warn, crit = None, None
        if "write_ios" in params:
            warn, crit = params["write_ios"]
            if writes >= crit:
                infos.append("Write operations: %d (!!)" % (writes))
                status = 2
            elif writes >= warn:
                infos.append("Write operations: %d (!)" % (writes))
                status = max(status, 1)
        else:
            warn, crit = None, None
        ios = reads + writes
        ios_per_sec = get_rate(countername + ".ios", this_time, ios)
        infos.append("IOs: %.2f/sec" % ios_per_sec)

        if params.get("latency_perfdata"):
            perfdata.append(("ios", ios_per_sec))

    # Do Latency computation if this information is available:
    if len(line) >= 7 and line[6] >= 0:
        timems = int(line[6])
        timems_per_sec = get_rate(countername + ".time", this_time, timems)
        if not ios_per_sec:
            latency = 0.0
        else:
            latency = timems_per_sec / ios_per_sec  # fixed: true-division
        infos.append("Latency: %.2fms" % latency)
        if "latency" in params:
            warn, crit = params["latency"]
            if latency >= crit:
                status = 2
                infos[-1] += "(!!)"
            elif latency >= warn:
                status = max(status, 1)
                infos[-1] += "(!)"
        else:
            warn, crit = None, None

        if params.get("latency_perfdata"):
            perfdata.append(("latency", latency, warn, crit))

    # Queue Lengths (currently only Windows). Windows uses counters here.
    # I have not understood, why....
    if len(line) >= 9:
        for what, ctr in [("read", line[7]), ("write", line[8])]:
            countername = "diskstat.%s.ql.%s" % (item, what)
            levels = params.get(what + "_ql")
            if levels:
                warn, crit = levels
            else:
                warn, crit = None, None

            qlx = get_rate(countername, this_time, int(ctr))
            ql = qlx / 10000000.0
            infos.append(what.title() + " Queue: %.2f" % ql)

            # check levels
            if levels is not None:
                if ql >= crit:
                    status = 2
                    infos[-1] += "(!!)"
                elif ql >= warn:
                    status = max(status, 1)
                    infos[-1] += "(!)"

            if params.get("ql_perfdata"):
                perfdata.append((what + "_ql", ql))

    return (status, ", ".join(infos), perfdata)


def check_diskstat_generic(
    item: str,
    params: Mapping[str, Any],
    this_time: float,
    info: Sequence[Sequence[Any]],
    mode: str = "sectors",
) -> Union[
    Tuple[int, str],
    Tuple[int, str, Sequence[Tuple[str, str]]],
    Tuple[
        int,
        str,
        MutableSequence[Any],
    ],
]:
    # legacy version if item is "read" or "write"
    if item in ["read", "write"]:
        return _check_diskstat_old(item, params, this_time, info)

    # Sum up either all physical disks (if item is "SUMMARY") or
    # all entries matching the item in question. It is not a bug if
    # a disk appears more than once. This can for example happen in
    # Windows clusters - even if they are no Checkmk clusters.

    summed_up: Sequence[int] = [0] * 13
    matching = 0

    has_multiple_nodes = len(set(line[0] for line in info)) > 1
    if item == "SUMMARY" and has_multiple_nodes:
        return 3, "summary mode not supported in a cluster"

    for line in info:
        if item == "SUMMARY" and " " in line[1]:
            continue  # skip non-physical disks

        elif item == "SUMMARY" or line[1] == item:
            matching += 1
            summed_up = [x + int(y) for x, y in zip(summed_up, line[2:])]

    if matching == 0:
        return 3, "No matching disk found"
    return check_diskstat_line(this_time, item, params, [None, ""] + summed_up, mode)  # type:ignore


# This is the legacy version of diskstat as used in <= 1.1.10.
# We keep it here for a while in order to be compatible with
# old installations.
def _check_diskstat_old(
    item: str, params: Any, this_time: float, info: Sequence[Sequence[Any]]
) -> Union[Tuple[int, str], Tuple[int, str, Sequence[Tuple[str, str]]]]:
    # sum up over all devices
    if item == "read":
        index = 2  # sectors read
    elif item == "write":
        index = 3  # sectors written
    else:
        return (3, "invalid item %s" % (item,))

    this_val = 0
    for line in info:
        if line[0] is not None:
            return 3, "read/write mode not supported in a cluster"
        if " " not in line[1]:
            this_val += int(line[index])

    per_sec = get_rate("diskstat." + item, this_time, this_val)
    mb_per_s = per_sec / 2048.0  # Diskstat output is in sectors a 512 Byte
    kb_per_s = per_sec / 2.0
    perfdata = [(item, "%f" % kb_per_s)]
    return (0, "%.1f MB/s" % mb_per_s, perfdata)


# .
#   .--Dict based API------------------------------------------------------.
#   |  ____  _      _     _                        _      _    ____ ___    |
#   | |  _ \(_) ___| |_  | |__   __ _ ___  ___  __| |    / \  |  _ \_ _|   |
#   | | | | | |/ __| __| | '_ \ / _` / __|/ _ \/ _` |   / _ \ | |_) | |    |
#   | | |_| | | (__| |_  | |_) | (_| \__ \  __/ (_| |  / ___ \|  __/| |    |
#   | |____/|_|\___|\__| |_.__/ \__,_|___/\___|\__,_| /_/   \_\_|  |___|   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  The newest generation of Disk IO checks parse all informatin info   |
#   |  a dictionary, where counters are aleady resolved. Look at diskstat  |
#   |  (the Linux diskstat check) for an example.                          |
#   '----------------------------------------------------------------------'


# ==================================================================================================
# ==================================================================================================
# THIS FUNCTION HAS BEEN MIGRATED TO THE NEW CHECK API (OR IS IN THE PROCESS), PLEASE DO NOT TOUCH
# IT. INSTEAD, MODIFY THE MIGRATED VERSION.
# ==================================================================================================
# ==================================================================================================
def diskstat_select_disk(  # pylint: disable=too-many-branches
    disks: Mapping[str, MutableMapping[str, Any]], item: str
) -> Optional[MutableMapping[str, Any]]:

    # In summary mode we add up the throughput values, but
    # we average the other values for disks that have a throughput
    # > 0. Note: This is not very precise. Strictly spoken
    # we would need to do the summarization directly in the
    # parse function. But there we do not have information about
    # the physical multipath devices and would add up the traffic
    # of the paths with the traffice of the device itself....

    if item == "SUMMARY":
        summarized: MutableMapping[str, Any] = {
            "node": None,
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
        }

        if disks:
            num_averaged = 0
            for device, disk in disks.items():
                # If all disks are idle the summarized dict would have no keys
                # So we take care that at least all keys of this disk are set
                for key in disk:
                    if key != "node":
                        summarized.setdefault(key, 0.0)

                if device.startswith("LVM "):
                    continue  # skip LVM devices for summary

                num_averaged += 1
                for key, value in disk.items():
                    if key != "node":
                        summarized[key] += value

            if num_averaged:
                for key, value in summarized.items():
                    if key.startswith("ave") or key in _METRICS_TO_BE_AVERAGED:
                        summarized[key] /= num_averaged

        return summarized

    elif item not in disks:
        return None

    else:
        return disks[item]


# New version for this diskstat checks that use the new dict
# format. The first one is "diskstat" - the Linux version of
# this check. Look there for examples of the format of the
# dictionary "disks". Example:
# disks = { "sda" : {
#       'node'                       : None,
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
# ==================================================================================================
# ==================================================================================================
# THIS FUNCTION HAS BEEN MIGRATED TO THE NEW CHECK API (OR IS IN THE PROCESS), PLEASE DO NOT TOUCH
# IT. INSTEAD, MODIFY THE MIGRATED VERSION.
# ==================================================================================================
# ==================================================================================================
def check_diskstat_dict(  # pylint: disable=too-many-branches
    item: str, params: Mapping[str, Any], disks: Mapping[str, MutableMapping[str, Any]]
) -> Iterable[Any]:
    # Take care of previously discovered services
    if item in ("read", "write"):
        yield 3, "Sorry, the new version of this check does not support one service for read and one for write anymore."
        return

    this_time = time.time()
    disk = diskstat_select_disk(disks, item)
    if not disk:
        return

    # Averaging
    # Note: this check uses a simple method of averaging: As soon as averaging
    # is turned on the actual metrics are *replaced* by the averaged ones. No
    # duplication of performance data or check output here. This is because we
    # have so many metrics...
    prefix = ""
    averaging = params.get("average")  # in seconds here!
    if averaging:
        avg_disk = {}  # Do not modify our arguments!!
        for key, value in disk.items():
            if isinstance(value, (int, float)):
                avg_disk[key] = get_average(
                    "diskstat.%s.%s.avg" % (item, key), this_time, value, averaging / 60.0
                )
            else:
                avg_disk[key] = value
        disk = avg_disk

        prefix = "%s average: " % get_age_human_readable(averaging)

    # Utilization
    if "utilization" in disk:
        util = disk.pop("utilization")
        yield check_levels(
            util,
            "disk_utilization",
            params.get("utilization"),
            human_readable_func=lambda x: get_percent_human_readable(x * 100.0),
            scale=0.01,
            statemarkers=False,
            infoname=prefix + "Utilization",
        )

    # Throughput
    for what in "read", "write":
        if what + "_throughput" in disk:
            throughput = disk.pop(what + "_throughput")
            yield check_levels(
                throughput,
                "disk_" + what + "_throughput",
                params.get(what),
                scale=1048576,
                statemarkers=False,
                human_readable_func=render.iobandwidth,
                infoname=what.title(),
            )

    # Average wait from end to end
    for what in ["wait", "read_wait", "write_wait"]:
        if "average_" + what in disk:
            wait = disk.pop("average_" + what)
            yield check_levels(
                wait,
                "disk_average_" + what,
                params.get(what),
                unit="ms",
                scale=0.001,
                statemarkers=False,
                infoname="Average %s" % what.title().replace("_", " "),
            )

    # Average disk latency
    if "latency" in disk:
        latency = disk.pop("latency")
        yield check_levels(
            latency,
            "disk_latency",
            params.get("latency"),
            unit="ms",
            scale=0.001,
            statemarkers=False,
            infoname="Latency",
        )

    # Read/write disk latency
    for what in ["read", "write"]:
        latency_key = "%s_latency" % what
        if latency_key not in disk:
            continue
        latency = disk.pop(latency_key)
        if latency is not None:
            yield check_levels(
                latency,
                "disk_%s" % latency_key,
                params.get(latency_key),
                unit="ms",
                scale=0.001,
                statemarkers=False,
                infoname="%s latency" % what.title(),
            )

    # Queue lengths
    for what, plugin_text in [
        ("queue_length", "Queue Length"),
        ("read_ql", "Read Queue Length"),
        ("write_ql", "Write Queue Length"),
    ]:
        if what in disk:
            ql = disk.pop(what)
            yield check_levels(
                ql,
                "disk_" + what,
                params.get(what),
                statemarkers=False,
                infoname="Average %s" % plugin_text,
            )

    # I/O operations
    for what in "read", "write":
        if what + "_ios" in disk:
            ios = disk.pop(what + "_ios")
            yield check_levels(
                ios,
                "disk_" + what + "_ios",
                params.get(what + "_ios"),
                unit="1/s",
                statemarkers=False,
                infoname="%s operations" % what.title(),
            )

    # All the other metrics are currently not output in the plugin output - simply because
    # of their amount. They are present as performance data and will shown in graphs.

    # Send everything as performance data now. Sort keys alphabetically
    perfdata = []
    for key in sorted(disk):
        value = disk[key]
        if isinstance(value, (int, float)):
            # Currently the levels are not shown in the perfdata
            perfdata.append(("disk_" + key, value))

    if perfdata:
        yield 0, "", perfdata
