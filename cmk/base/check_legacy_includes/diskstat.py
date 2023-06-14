#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=consider-using-in
# pylint: disable=no-else-continue
# pylint: disable=no-else-return

from collections.abc import Mapping, MutableSequence, Sequence
from typing import Any

from cmk.base.check_api import check_levels, get_average, get_rate
from cmk.base.plugins.agent_based.agent_based_api.v1 import render


def check_diskstat_line(  # pylint: disable=too-many-branches
    this_time: float,
    item: str,
    params: Mapping[str, Any],
    line: Sequence[Any],
    mode: str = "sectors",
) -> tuple[int, str, MutableSequence[Any],]:
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
            countername = f"diskstat.{node}.{item}.{what}"
        else:
            countername = f"diskstat.{item}.{what}"

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
            countername = f"diskstat.{item}.ql.{what}"
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
