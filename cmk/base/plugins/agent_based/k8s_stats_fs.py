#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections
from contextlib import suppress
from typing import Any, Mapping, MutableMapping

from .agent_based_api.v1 import get_value_store, GetRateError, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_LEVELS
from .utils.k8s import Section, to_filesystem

###########################################################################
# NOTE: This check (and associated special agent) is deprecated and will be
#       removed in Checkmk version 2.2.
###########################################################################


def discover_k8s_stats_fs(section: Section) -> DiscoveryResult:
    """
    >>> for service in discover_k8s_stats_fs({
    ...     'filesystem': {'/dev/sda1': [{'capacity': 17293533184, 'available': 12933038080}]},
    ...     'interfaces': {"not": "needed"},
    ...     'timestamp': 1553765630.0,
    ... }):
    ...   print(service)
    Service(item='/dev/sda1')
    """
    yield from (
        Service(item=device)
        for device in section["filesystem"]
        if device not in {"tmpfs", "rootfs", "/dev/shm"}
        if not (
            isinstance(device, str)
            and (device.startswith("/var/lib/docker/") or device.startswith("overlay"))  #
        )
    )


def _check__k8s_stats_fs__core(
    value_store: MutableMapping[str, Any],
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """
    >>> value_store = {'/dev/sda1.delta': (1553765630.0, 4158.4921875)}
    >>> for result in _check__k8s_stats_fs__core(value_store, "/dev/sda1", {}, {
    ...       'filesystem': {"/dev/sda1": [{'capacity': 17293533184, 'available': 12933038080}]},
    ...       'timestamp': 1553765631.0,
    ... }):
    ...     print(result)
    Metric('fs_used', 4158.4921875, levels=(13193.91875, 14843.15859375), boundaries=(0.0, 16492.3984375))
    Metric('fs_size', 16492.3984375, boundaries=(0.0, None))
    Metric('fs_used_percent', 25.21459933956316, levels=(80.0, 90.0), boundaries=(0.0, 100.0))
    Result(state=<State.OK: 0>, summary='25.21% used (4.06 of 16.1 GiB)')
    Metric('growth', 0.0)
    Result(state=<State.OK: 0>, summary='trend per 1 day 0 hours: +0 B')
    Result(state=<State.OK: 0>, summary='trend per 1 day 0 hours: +0%')
    Metric('trend', 0.0, boundaries=(0.0, 687.1832682291666))
    """
    now = section["timestamp"]
    empty: collections.Counter[str] = collections.Counter()
    disk = to_filesystem(
        sum(
            (collections.Counter(interface) for interface in section["filesystem"][item]),
            empty,
        )
    )

    with suppress(GetRateError):
        yield from df_check_filesystem_single(
            value_store=value_store,
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
    params: Mapping[str, Any],
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
