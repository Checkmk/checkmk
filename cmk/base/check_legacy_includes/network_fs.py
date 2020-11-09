#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from cmk.base.check_api import get_parsed_item_data

from .df import df_check_filesystem_single

# <<<...mounts>>>
# /foobar hanging 0 0 0 0
# /with spaces ok 217492 123563 112515 524288
# /with spaces Permission denied


def parse_network_fs_mounts(info):
    parsed = {}
    for line in info:
        if " ".join(line[-2:]) == "Permission denied":
            parsed.setdefault(" ".join(line[:-2]), {"state": "Permission denied"})

        else:
            parsed.setdefault(" ".join(line[:-5]), {
                "state": line[-5],
                "data": line[-4:],
            })

    return parsed


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


@get_parsed_item_data
def check_network_fs_mounts(item, params, attrs):
    params = params or {}

    state = attrs["state"]
    if state == "Permission denied":
        return 2, "Permission denied"
    if state == "hanging":
        return 2, "Server not responding"
    if state != 'ok':
        return 2, "Unknown state: %s" % state

    data = attrs["data"]
    if data == ['-', '-', '-', '-']:
        return 0, "Mount seems OK"
    size_blocks, _, free_blocks, blocksize = map(int, data)

    if size_blocks <= 0 or free_blocks < 0 or blocksize > 16.0 * MEGA:
        return 2, "Stale fs handle"

    to_mb = blocksize / MEGA
    size_mb = size_blocks * to_mb
    free_mb = free_blocks * to_mb

    state, text, perf = df_check_filesystem_single(item, size_mb, free_mb, 0, None, None, params)

    if not params.get("has_perfdata"):
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
