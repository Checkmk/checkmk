#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping, MutableMapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
)
from cmk.plugins.lib import diskstat

from .lib import SectionPodmanContainerStats


def discover_podman_container_diskstat(
    section: SectionPodmanContainerStats,
) -> DiscoveryResult:
    yield Service(item="SUMMARY")


def check_podman_container_diskstat(
    item: str, params: Mapping[str, object], section: SectionPodmanContainerStats
) -> CheckResult:
    yield from _check_diskstat_testable(
        params=params,
        read_ios=section.read_io,
        write_ios=section.write_io,
        value_store=get_value_store(),
        this_time=time.time(),
    )


def _check_diskstat_testable(
    read_ios: int,
    write_ios: int,
    params: Mapping[str, object],
    value_store: MutableMapping[str, object],
    this_time: float,
) -> CheckResult:
    yield from diskstat.check_diskstat_dict(
        params=params,
        disk={
            "read_ios": read_ios,
            "write_ios": write_ios,
        },
        value_store=value_store,
        this_time=this_time,
    )


check_plugin_podman_container_diskstat = CheckPlugin(
    name="podman_container_diskstat",
    service_name="Container IO %s",
    sections=["podman_container_stats"],
    discovery_function=discover_podman_container_diskstat,
    check_function=check_podman_container_diskstat,
    check_ruleset_name="diskstat",
    check_default_parameters={},
)
