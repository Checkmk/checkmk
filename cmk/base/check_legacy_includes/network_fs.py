#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Final, Mapping, NamedTuple, Optional

from cmk.base.api.agent_based.type_defs import StringTable

from .df import df_check_filesystem_single

# <<<...mounts>>>
# /foobar hanging 0 0 0 0
# /with spaces ok 217492 123563 112515 524288
# /with spaces Permission denied


CHECK_DEFAULT_PARAMETERS: Final = {
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


NetworkFSSection = dict[str, NetworkFSMount]


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


def _scaled_metric(new_name, metric, factor):
    metric_def_as_list = [new_name]
    for value in metric[1:]:
        try:
            metric_def_as_list.append(factor * value)
        except TypeError:
            metric_def_as_list.append(None)
    return tuple(metric_def_as_list)


def check_network_fs_mounts(
    item: str,
    params: Mapping[str, Any],
    section: NetworkFSSection,
):
    if not (mount := section.get(item)):
        return

    if mount.state == "Permission denied":
        return 2, "Permission denied"
    if mount.state == "hanging":
        return 2, "Server not responding"
    if mount.state != "ok":
        return 2, "Unknown state: %s" % mount.state

    if not (usage := mount.usage):
        return
    if usage == ("-", "-", "-", "-"):
        return 0, "Mount seems OK"

    size_blocks, _, free_blocks, blocksize = map(int, usage)

    if size_blocks <= 0 or free_blocks < 0 or blocksize > 16.0 * MEGA:
        return 2, "Stale fs handle"

    to_mb = blocksize / MEGA
    size_mb = size_blocks * to_mb
    free_mb = free_blocks * to_mb

    state, text, perf = df_check_filesystem_single(item, size_mb, free_mb, 0, None, None, params)

    if not params["has_perfdata"]:
        return state, text

    # fix metrics to new names and scales
    new_perf = [_scaled_metric("fs_used", perf[0], MEGA)]
    old_perf_dict = {metric[0]: metric for metric in perf[1:]}
    for old_name, new_name, factor in (
        ("fs_size", "fs_size", MEGA),
        ("growth", "fs_growth", MB_PER_DAY_TO_B_PER_S),
        ("trend", "fs_trend", MB_PER_DAY_TO_B_PER_S),
    ):
        metric = old_perf_dict.get(old_name)
        if metric is not None:
            new_perf.append(_scaled_metric(new_name, metric, factor))

    return state, text, new_perf
