#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from typing import NamedTuple
from ..agent_based_api.v1.type_defs import StringTable, DiscoveryResult, CheckResult
from ..agent_based_api.v1 import get_value_store, get_rate, Service
from ..utils.cpu_util import check_cpu_util


class CpuSection(NamedTuple):
    uptime: float
    num_cpus: int
    usage_usec: int


def parse_cpu(string_table: StringTable) -> CpuSection:
    parsed = {line[0]: line[1:] for line in string_table}
    return CpuSection(
        uptime=float(parsed['uptime'][0]),
        num_cpus=int(parsed['num_cpus'][0]),
        usage_usec=int(parsed['usage_usec'][0]),
    )


def check_cpu(params: Mapping[str, Any], section: CpuSection) -> CheckResult:
    value_store = get_value_store()
    yield from _check_cpu(value_store, params, section)


def _check_cpu(value_store, params: Mapping[str, Any], section: CpuSection) -> CheckResult:
    this_time = section.uptime
    # https://github.com/containerd/cri/blob/bc08a19f3a44bda9fd141e6ee4b8c6b369e17e6b/pkg/server/container_stats_list_linux.go#L85
    # https://github.com/moby/moby/blob/64bd4485b3a66a597c02c95f5776395e540b2c7c/daemon/daemon_unix.go#L1528
    util = get_rate(value_store, 'cpu_usage', this_time,
                    (section.usage_usec) / 1000_000 / section.num_cpus) * 100
    yield from check_cpu_util(
        util=util,
        params=params,
        value_store=value_store,
        this_time=this_time,
    )


def discover_cpu(section: CpuSection) -> DiscoveryResult:
    yield Service()
