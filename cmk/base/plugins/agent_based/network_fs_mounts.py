#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Final, Mapping, NamedTuple, Optional, Union

from .agent_based_api.v1 import get_value_store, Metric, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.df import df_check_filesystem_single

DEFAULT_NETWORK_FS_MOUNT_PARAMETERS: Final = {
    # adapted from FILESYSTEM_DEFAULT_LEVELS:
    "levels": (80.0, 90.0),
    "magic_normsize": 20,
    "levels_low": (50.0, 60.0),
    "trend_range": 24,
    "trend_perfdata": True,
    "has_perfdata": False,
    "show_levels": "onmagic",
}


class NetworkFSUsage(NamedTuple):
    total_blocks: str
    free_blocks_su: str
    free_blocks: str
    blocksize: str


class NetworkFSMount(NamedTuple):
    mountpoint: str
    state: str
    usage: Optional[NetworkFSUsage]


NetworkFSSection = Mapping[str, NetworkFSMount]


def parse_network_fs_mounts(string_table: StringTable) -> NetworkFSSection:
    section: dict[str, NetworkFSMount] = {}
    for entry in string_table:
        if " ".join(entry[-2:]) == "Permission denied":
            section.setdefault(
                " ".join(entry[:-2]),
                NetworkFSMount(
                    mountpoint=" ".join(entry[:-2]),
                    state="Permission denied",
                    usage=None,
                ),
            )
            continue
        section.setdefault(
            " ".join(entry[:-5]),
            NetworkFSMount(
                mountpoint=" ".join(entry[:-5]),
                state=entry[-5],
                usage=NetworkFSUsage(
                    total_blocks=entry[-4],
                    free_blocks_su=entry[-3],
                    free_blocks=entry[-2],
                    blocksize=entry[-1],
                ),
            ),
        )
    return section


MEGA = 1048576.0

MB_PER_DAY_TO_B_PER_S = MEGA / 86400.0


def _scaled_metric(new_name: str, metric: Metric, factor: float) -> Metric:
    return Metric(
        new_name,
        metric.value * factor,
        levels=(
            metric.levels[0] * factor if metric.levels[0] is not None else None,
            metric.levels[1] * factor if metric.levels[1] is not None else None,
        )
        if metric.levels
        else None,
        boundaries=(
            metric.boundaries[0] * factor if metric.boundaries[0] is not None else None,
            metric.boundaries[1] * factor if metric.boundaries[1] is not None else None,
        )
        if metric.boundaries
        else None,
    )


def discover_network_fs_mounts(section: NetworkFSSection) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_network_fs_mount(
    item: str,
    params: Mapping[str, Any],
    section: NetworkFSSection,
) -> CheckResult:
    if not (mount := section.get(item)):
        return

    if mount.state == "Permission denied":
        yield Result(state=State.CRIT, summary="Permission denied")
        return
    if mount.state == "hanging":
        yield Result(state=State.CRIT, summary="Server not responding")
        return
    if mount.state != "ok":
        yield Result(state=State.CRIT, summary="Unknown state: %s" % mount.state)
        return

    if not (usage := mount.usage):
        return
    if usage == ("-", "-", "-", "-"):
        yield Result(state=State.OK, summary="Mount seems OK")
        return

    size_blocks, _, free_blocks, blocksize = map(int, usage)

    if size_blocks <= 0 or free_blocks < 0 or blocksize > 16.0 * MEGA:
        yield Result(state=State.CRIT, summary="Stale fs handle")
        return

    to_mb = blocksize / MEGA
    size_mb = size_blocks * to_mb
    free_mb = free_blocks * to_mb

    entries = list(
        df_check_filesystem_single(
            value_store=get_value_store(),
            mountpoint=item,
            size_mb=size_mb,
            avail_mb=free_mb,
            reserved_mb=0,
            inodes_total=None,
            inodes_avail=None,
            params=params,
        )
    )

    results: list[Union[Result, Metric]] = []
    metrics: dict[str, Metric] = {}
    for entry in entries:
        if isinstance(entry, Result):
            results.append(entry)
        if isinstance(entry, Metric):
            metrics.setdefault(entry[0], entry)

    if not params.get("has_perfdata", False):
        yield from results
        return

    for old_name, new_name, factor in (
        ("fs_used", "fs_used", MEGA),
        ("fs_size", "fs_size", MEGA),
        ("growth", "fs_growth", MB_PER_DAY_TO_B_PER_S),
        ("trend", "fs_trend", MB_PER_DAY_TO_B_PER_S),
    ):
        metric = metrics.get(old_name)
        if metric is not None:
            results.append(_scaled_metric(new_name, metric, factor))
    yield from results


register.agent_section(
    name="nfsmounts",
    parse_function=parse_network_fs_mounts,
)


register.check_plugin(
    name="nfsmounts",
    service_name="NFS mount %s",
    discovery_function=discover_network_fs_mounts,
    check_function=check_network_fs_mount,
    check_ruleset_name="network_fs",
    check_default_parameters=DEFAULT_NETWORK_FS_MOUNT_PARAMETERS,
)


register.agent_section(
    name="cifsmounts",
    parse_function=parse_network_fs_mounts,
)


register.check_plugin(
    name="cifsmounts",
    service_name="CIFS mount %s",
    discovery_function=discover_network_fs_mounts,
    check_function=check_network_fs_mount,
    check_ruleset_name="network_fs",
    check_default_parameters=DEFAULT_NETWORK_FS_MOUNT_PARAMETERS,
)
