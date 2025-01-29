#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ported by (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Service

Section = Mapping[str, Mapping[str, Any]]


def discovery_prism_cluster_io(section: Section) -> DiscoveryResult:
    stat_keys = (
        "controller_io_bandwidth_kBps",
        "controller_num_iops",
        "controller_avg_io_latency_usecs",
    )
    if {*stat_keys} <= section.get("stats", {}).keys():
        yield Service()


def check_prism_cluster_io(params: Mapping[str, Any], section: Section) -> CheckResult:
    iobw_used = section.get("stats", {}).get("controller_io_bandwidth_kBps")
    if iobw_used:
        iobw_usage = int(iobw_used) / 10000
        yield from check_levels_v1(
            iobw_usage,
            levels_upper=params["io"],
            metric_name="prism_cluster_iobw",
            label="I/O Bandwidth",
            render_func=lambda d: f"{d:.2f} MB/s",
        )

    iops_used = section.get("stats", {}).get("controller_num_iops")
    if iops_used:
        iops_usage = int(iops_used) / 10000
        yield from check_levels_v1(
            iops_usage,
            levels_upper=params["iops"],
            metric_name="prism_cluster_iops",
            label="IOPS",
        )

    iolatency_raw = section.get("stats", {}).get("controller_avg_io_latency_usecs")
    if iolatency_raw:
        iolatency = int(iolatency_raw) / 1000

        yield from check_levels_v1(
            iolatency,
            levels_upper=params["iolat"],
            metric_name="prism_cluster_iolatency",
            label="I/O Latency",
            render_func=lambda d: f"{d:.1f} ms",
        )


check_plugin_prism_cluster_io = CheckPlugin(
    name="prism_cluster_io",
    service_name="NTNX Cluster Controller IO",
    sections=["prism_info"],
    discovery_function=discovery_prism_cluster_io,
    check_function=check_prism_cluster_io,
    check_default_parameters={
        "io": (500.0, 1000.0),
        "iops": (10000, 20000),
        "iolat": (500.0, 1000.0),
    },
    check_ruleset_name="prism_cluster_io",
)
