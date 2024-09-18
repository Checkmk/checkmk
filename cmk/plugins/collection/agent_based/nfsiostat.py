#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

# example output
#
# y.y.y.y:/mount/name mounted on /var/log/da:
#
# op/s         rpc bklog
# 2579.20            0.00
# read:             ops/s            kB/s           kB/op         retrans         avg RTT (ms)    avg exe (ms)
#                0.000           0.000           0.000        0 (0.0%)           0.000           0.000
# write:            ops/s            kB/s           kB/op         retrans         avg RTT (ms)    avg exe (ms)
#              2578.200        165768.087       64.296        0 (0.0%)          21.394         13980.817
#
# x.x.x.x:/mount/name mounted on /data:
# ...
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    StringTable,
)


@dataclass(frozen=True)
class Mount:
    op_s: float
    rpc_backlog: float
    read_ops: float
    read_b_s: float
    read_b_op: float
    read_retrans: float
    read_avg_rtt_s: float
    read_avg_exe_s: float
    write_ops_s: float
    write_b_s: float
    write_b_op: float
    write_retrans: float
    write_avg_rtt_s: float
    write_avg_exe_s: float


Section = Mapping[str, Mount]


def parse_nfsiostat(string_table: StringTable) -> Section:
    # removes double list
    [new_info] = string_table
    import re

    # Result is a dictionary with mountpoint as key and a list of (currently 16)
    # metrics. Metrics are in the same order, from left to right, top to bottom,
    # as in the output of nfsiostat.
    # The first regex group (m0) identifies the mountpount and the second group
    # (m1) provides a space separated list of metrics.
    # Future expandibility or changes to the nfsiostat command will require
    # at most a re-ordering of these values (in check_nfsiostat_parames) and
    # changing the check to include new metrics (via swtiches/flags)
    NUMBER = r"(\d+\.\d+|\d+)"
    NUMBER_SEPARATOR = r"[() %]+"
    NUMBERS = NUMBER_SEPARATOR.join([NUMBER] * 7)
    # we want to read the first seven numbers after read: and write:
    # nfsiostat is able to report more numbers for read and write, but we just care about the
    # first seven. note that the NUMBER_SEPARATOR trick only works because the first and last number
    # on our list is not in brackets.
    matches = re.findall(
        rf"(\S+:\S+) mounted on \S+:.*?{NUMBER_SEPARATOR.join([NUMBER] * 2)}.*?read:.*?{NUMBERS}.*?write:.*?{NUMBERS}",
        " ".join(new_info),
        flags=re.DOTALL,
    )
    # Note we skip elements 6 and 13 (non-% retransmission)
    return {
        f"'{m[0]}',": Mount(
            op_s=float(m[1]),
            rpc_backlog=float(m[2]),
            read_ops=float(m[3]),
            read_b_s=float(m[4]),
            read_b_op=float(m[5]),
            read_retrans=float(m[7]),
            read_avg_rtt_s=float(m[8]) / 1000.0,
            read_avg_exe_s=float(m[9]) / 1000.0,
            write_ops_s=float(m[10]),
            write_b_s=float(m[11]),
            write_b_op=float(m[12]),
            write_retrans=float(m[14]),
            write_avg_rtt_s=float(m[15]) / 1000.0,
            write_avg_exe_s=float(m[16]) / 1000.0,
        )
        for m in matches
    }


agent_section_nfsiostat = AgentSection(name="nfsiostat", parse_function=parse_nfsiostat)


def inventory_nfsiostat(section: Section) -> DiscoveryResult:
    for mountname in section:
        yield Service(item=mountname)


def check_nfsiostat(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (values := section.get(item)) is None:
        return

    yield from check_levels_v1(
        values.op_s,
        metric_name="op_s",
        levels_upper=params.get("op_s"),
        label="Operations",
        render_func=lambda f: "%.2f/s" % f,
    )
    yield from check_levels_v1(
        values.rpc_backlog,
        metric_name="rpc_backlog",
        levels_upper=params.get("rpc_backlog"),
        label="RPC Backlog",
        render_func=lambda f: "%.2f" % f,
    )
    yield from check_levels_v1(
        values.read_ops,
        metric_name="read_ops",
        levels_upper=params.get("read_ops"),
        label="Read operations",
        render_func=lambda f: "%.2f/s" % f,
    )
    yield from check_levels_v1(
        values.read_b_s,
        metric_name="read_b_s",
        levels_upper=params.get("read_b_s"),
        label="Reads size",
        render_func=render.iobandwidth,
    )
    yield from check_levels_v1(
        values.read_b_op,
        metric_name="read_b_op",
        levels_upper=params.get("read_b_op"),
        label="Read bytes per operation",
        render_func=lambda f: "%.2f B/op" % f,
    )
    yield from check_levels_v1(
        values.read_retrans,
        metric_name="read_retrans",
        levels_upper=params.get("read_retrans"),
        label="Read Retransmission",
        render_func=render.percent,
    )
    yield from check_levels_v1(
        values.read_avg_rtt_s,
        metric_name="read_avg_rtt_s",
        levels_upper=params.get("read_avg_rtt_s"),
        label="Read average RTT",
        render_func=render.timespan,
    )
    yield from check_levels_v1(
        values.read_avg_exe_s,
        metric_name="read_avg_exe_s",
        levels_upper=params.get("read_avg_exe_s"),
        label="Read average EXE",
        render_func=render.timespan,
    )
    yield from check_levels_v1(
        values.write_ops_s,
        metric_name="write_ops_s",
        levels_upper=params.get("write_ops_s"),
        label="Write operations",
        render_func=lambda f: "%.2f/s" % f,
    )
    yield from check_levels_v1(
        values.write_b_s,
        metric_name="write_b_s",
        levels_upper=params.get("write_b_s"),
        label="Writes size",
        render_func=render.iobandwidth,
    )
    yield from check_levels_v1(
        values.write_b_op,
        metric_name="write_b_op",
        levels_upper=params.get("write_b_op"),
        label="Write bytes per operation",
        render_func=lambda f: "%.2f B/op" % f,
    )
    yield from check_levels_v1(
        values.write_retrans,
        metric_name="write_retrans",
        levels_upper=params.get("write_retrans"),
        label="Write Retransmission",
        render_func=render.percent,
    )
    yield from check_levels_v1(
        values.write_avg_rtt_s,
        metric_name="write_avg_rtt_s",
        levels_upper=params.get("write_avg_rtt_s"),
        label="Write Average RTT",
        render_func=render.timespan,
    )
    yield from check_levels_v1(
        values.write_avg_exe_s,
        metric_name="write_avg_exe_s",
        levels_upper=params.get("write_avg_exe_s"),
        label="Write Average EXE",
        render_func=render.timespan,
    )


check_plugin_nfsiostat = CheckPlugin(
    name="nfsiostat",
    service_name="NFS IO stats %s",
    discovery_function=inventory_nfsiostat,
    check_function=check_nfsiostat,
    check_ruleset_name="nfsiostats",
    check_default_parameters={},
)
