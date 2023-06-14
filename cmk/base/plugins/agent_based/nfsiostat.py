#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from typing import Any, Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import check_levels, register, Service
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)


@dataclass(frozen=True)
class Config:
    metric: str
    title: str
    fmt: str

    def render(self, value: float) -> str:
        return self.fmt % value


# Map the 16 metric items from nfsiostat to cmk results/metrics.
# Note we skip 5 and 12.
metric_config: Mapping[int, Config] = {
    0: Config("op_s", "Operations", "%.2f/s"),
    1: Config("rpc_backlog", "RPC Backlog", "%.2f"),
    2: Config("read_ops", "Read operations /s", "%.3f/s"),
    3: Config("read_b_s", "Reads size /s", "%.3fB/s"),
    4: Config("read_b_op", "Read bytes per operation", "%.3fB/op"),
    6: Config("read_retrans", "Read Retransmission", "%.1f%%"),
    7: Config("read_avg_rtt_ms", "Read average RTT", "%.3f/s"),
    8: Config("read_avg_exe_ms", "Read average EXE", "%.3f/s"),
    9: Config("write_ops_s", "Write operations /s", "%.3f/s"),
    10: Config("write_b_s", "Writes size /s", "%.3fkB/s"),
    11: Config("write_b_op", "Write bytes per operation", "%.3fB/op"),
    13: Config("write_retrans", "Write Retransmission", "%.3f%%"),
    14: Config("write_avg_rtt_ms", "Write Average RTT", "%.3f/ms"),
    15: Config("write_avg_exe_ms", "Write Average EXE", "%.3f/ms"),
}

Section = Mapping[str, str]


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
    return {
        f"'{m[0]}',": m[1:]
        for m in re.findall(
            r"(\S+:\S+) mounted on \S+:%s" % (r".*?(\d+\.\d+|\d+)" * 16),
            " ".join(new_info),
            flags=re.DOTALL,
        )
    }


register.agent_section(name="nfsiostat", parse_function=parse_nfsiostat)


def inventory_nfsiostat(section: Section) -> DiscoveryResult:
    for mountname in section:
        yield Service(item=mountname)


def check_nfsiostat(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if item not in section:
        return
    values = section[item]
    for count, value in enumerate(values):
        if (config := metric_config.get(count)) is not None:
            yield from check_levels(
                float(value),
                metric_name=config.metric,
                levels_upper=params.get(config.metric),
                label=config.title,
                render_func=config.render,
            )


register.check_plugin(
    name="nfsiostat",
    service_name="NFS IO stats %s",
    discovery_function=inventory_nfsiostat,
    check_function=check_nfsiostat,
    check_ruleset_name="nfsiostats",
    check_default_parameters={},
)
