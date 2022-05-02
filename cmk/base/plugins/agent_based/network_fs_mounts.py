#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from enum import Enum
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


class NetworkFSState(Enum):
    PERMISSION_DENIED = "Permission denied"
    HANGING = "hanging"
    OK = "ok"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value):
        return NetworkFSState.UNKNOWN


NetworkFSStateMapping: Mapping[NetworkFSState, State] = {
    NetworkFSState.PERMISSION_DENIED: State.CRIT,
    NetworkFSState.HANGING: State.CRIT,
    NetworkFSState.UNKNOWN: State.CRIT,
    NetworkFSState.OK: State.OK,
}


class NetworkFSUsage(NamedTuple):
    total_blocks: int
    free_blocks_su: int
    free_blocks: int
    blocksize: int


class NetworkFSMount(NamedTuple):
    mountpoint: str
    state: str
    mount_seems_okay: bool
    usage: Optional[NetworkFSUsage]
    source: Optional[str]


NetworkFSSection = Mapping[str, NetworkFSMount]


def parse_nfsmounts_v2(string_table: StringTable) -> NetworkFSSection:
    section: dict[str, NetworkFSMount] = {}
    for entry in string_table:
        data = json.loads(entry[0])
        section.setdefault(
            data["mountpoint"],
            NetworkFSMount(
                mountpoint=str(data["mountpoint"]),
                state=str(data["state"]),
                mount_seems_okay=bool(data.get("mount_seems_okay", False)),
                usage=NetworkFSUsage(
                    total_blocks=int(usage["total_blocks"]),
                    free_blocks_su=int(usage["free_blocks_su"]),
                    free_blocks=int(usage["free_blocks"]),
                    blocksize=int(usage["blocksize"]),
                )
                if (usage := data["usage"])
                else None,
                source=None if (s := data.get("source")) is None else str(s),
            ),
        )
    return section


def parse_network_fs_mounts(string_table: StringTable) -> NetworkFSSection:
    section: dict[str, NetworkFSMount] = {}
    for entry in string_table:
        if " ".join(entry[-2:]) == "Permission denied":
            section.setdefault(
                " ".join(entry[:-2]),
                NetworkFSMount(
                    mountpoint=" ".join(entry[:-2]),
                    state="Permission denied",
                    mount_seems_okay=False,
                    usage=None,
                    source=None,
                ),
            )
            continue
        section.setdefault(
            " ".join(entry[:-5]),
            NetworkFSMount(
                mountpoint=" ".join(entry[:-5]),
                state=entry[-5],
                mount_seems_okay=entry[-4:] == ["-", "-", "-", "-"],
                usage=NetworkFSUsage(
                    total_blocks=int(entry[-4]),
                    free_blocks_su=int(entry[-3]),
                    free_blocks=int(entry[-2]),
                    blocksize=int(entry[-1]),
                )
                if entry[-4:] != ["-", "-", "-", "-"]
                else None,
                source=None,
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

    if mount.source:
        yield Result(state=State.OK, summary=f"Device: {mount.source}")

    state = NetworkFSState(mount.state)
    if state is not NetworkFSState.OK:
        yield Result(
            state=NetworkFSStateMapping[state], summary=f"State: {state.value.capitalize()}"
        )
        return

    if mount.mount_seems_okay:
        yield Result(state=State.OK, summary="Mount seems OK")
        return
    if not (usage := mount.usage):
        return

    size_blocks, _, free_blocks, blocksize = usage

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


# this section was replaced by the nfsmounts_v2 section in the agents of Checkmk version 2.2
register.agent_section(
    name="nfsmounts",
    parse_function=parse_network_fs_mounts,
)

register.agent_section(
    name="nfsmounts_v2",
    parsed_section_name="nfsmounts",
    parse_function=parse_nfsmounts_v2,
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
