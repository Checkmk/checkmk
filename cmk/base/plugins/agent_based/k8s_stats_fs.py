#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections
from contextlib import suppress

from .agent_based_api.v1 import (
    register,
    Service,
    GetRateError,
    get_value_store,
)

from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    CheckResult,
    Parameters,
    ValueStore,
)
from .utils.k8s import (
    Section,
    Filesystem,
    to_filesystem,
)
from .utils.df import (
    df_check_filesystem_single,
    FILESYSTEM_DEFAULT_LEVELS,
)


def discover_k8s_stats_fs(section: Section) -> DiscoveryResult:
    """
    >>> for service in discover_k8s_stats_fs({
    ...     'filesystem': {'/dev/sda1': [{'capacity': 17293533184, 'available': 12933038080}]},
    ...     'interfaces': {"not": "needed"},
    ...     'timestamp': 1553765630.0,
    ... }):
    ...   print(service)
    Service(item='/dev/sda1', parameters={}, labels=[])
    """
    yield from (
        Service(item=device)
        for device in section["filesystem"]
        if device not in {"tmpfs", "rootfs", "/dev/shm"}
        if not (isinstance(device, str) and (device.startswith("/var/lib/docker/") or  #
                                             device.startswith("overlay"))))


def _check__k8s_stats_fs__core(
    value_store: ValueStore,
    item: str,
    params: Parameters,
    section: Section,
) -> CheckResult:
    """
    >>> value_store = {'unneeded./dev/sda1.delta': (1553765630.0, 4158.4921875)}
    >>> for result in _check__k8s_stats_fs__core(value_store, "/dev/sda1", {}, {
    ...       'filesystem': {"/dev/sda1": [{'capacity': 17293533184, 'available': 12933038080}]},
    ...       'timestamp': 1553765631.0,
    ... }):
    ...     print(result)
    Metric('fs_used', 4158.4921875, levels=(13193.91875, 14843.15859375), boundaries=(0.0, 16492.3984375))
    Metric('fs_size', 16492.3984375, levels=(None, None), boundaries=(None, None))
    Metric('fs_used_percent', 25.21459933956316, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='25.2% used (4.06  of 16.1 GiB)', details='25.2% used (4.06  of 16.1 GiB)')
    Metric('growth', 0.0, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='trend per 1 day 0 hours: +0 B', details='trend per 1 day 0 hours: +0 B')
    Result(state=<State.OK: 0>, summary='trend per 1 day 0 hours: +0%', details='trend per 1 day 0 hours: +0%')
    Metric('trend', 0.0, levels=(None, None), boundaries=(0.0, 687.1832682291666))
    """
    now = section['timestamp']
    disk: Filesystem = to_filesystem(
        sum((collections.Counter(interface) for interface in section["filesystem"][item]),
            collections.Counter()))

    with suppress(GetRateError):
        yield from df_check_filesystem_single(
            value_store=value_store,
            check="unneeded",
            mountpoint=item,
            size_mb=disk["capacity"] / 1024**2,
            avail_mb=disk["available"] / 1024**2,
            reserved_mb=0,
            inodes_total=disk["inodes"],
            inodes_avail=disk["inodes_free"],
            params=params,
            this_time=now,
        )


def check_k8s_stats_fs(
    item: str,
    params: Parameters,
    section: Section,
) -> CheckResult:
    """This is an API conformant wrapper for the more functional base functions"""
    yield from _check__k8s_stats_fs__core(
        get_value_store(),
        item,
        params,
        section,
    )


register.check_plugin(
    name="k8s_stats_fs",
    sections=["k8s_stats"],
    service_name="Filesystem %s",
    discovery_function=discover_k8s_stats_fs,
    check_default_parameters=FILESYSTEM_DEFAULT_LEVELS,
    check_ruleset_name="filesystem",
    check_function=check_k8s_stats_fs,
)
