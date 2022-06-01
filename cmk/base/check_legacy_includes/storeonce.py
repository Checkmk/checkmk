#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# tyxpe: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from cmk.base.check_api import get_bytes_human_readable

from .df import df_check_filesystem_list


def parse_storeonce_clusterinfo(info):
    parsed = {}
    for line in info:
        parsed[line[0]] = line[1]
    return parsed


def parse_storeonce_servicesets(info):
    parsed: dict = {}
    for line in info:
        if line[0].startswith("["):
            item = line[0]
            parsed[item] = {}
        else:
            parsed[item][line[0]] = line[1]
    return parsed


def translate_storeonce_status(status):
    translate_state = {
        "0": 3,  # Unknown
        "1": 0,  # OK
        "2": 0,  # Information
        "3": 1,  # Warning
        "4": 2,  # Critical
    }
    return translate_state[status]


def _get_storeonce_space_values(values, type_):
    key = "%s in bytes" % type_
    if key in values:
        return float(values[key]), 0, 0

    # combined(total) = local + cloud
    type_ = type_.replace(" Space", "")
    combined_key = "combined%sBytes" % type_
    cloud_key = "cloud%sBytes" % type_
    local_key = "local%sBytes" % type_
    return (
        float(values.get(combined_key, 0)),
        float(values.get(cloud_key, 0)),
        float(values.get(local_key, 0)),
    )


def check_storeonce_space(item, params, values):
    total_bytes, cloud_bytes, local_bytes = _get_storeonce_space_values(values, "Capacity")
    free_bytes, free_cloud_bytes, free_local_bytes = _get_storeonce_space_values(
        values, "Free Space"
    )

    factor = 1024 * 1024
    yield df_check_filesystem_list(
        item, params, [(item, total_bytes / factor, free_bytes / factor, 0)]
    )  # fixed: true-division

    if cloud_bytes:
        yield 0, "Total cloud: %s" % get_bytes_human_readable(cloud_bytes)
    if local_bytes:
        yield 0, "Total local: %s" % get_bytes_human_readable(local_bytes)
    if free_cloud_bytes:
        yield 0, "Free cloud: %s" % get_bytes_human_readable(free_cloud_bytes)
    if free_local_bytes:
        yield 0, "Free local: %s" % get_bytes_human_readable(free_local_bytes)

    dedupl_ratio_str = values.get("Deduplication Ratio") or values.get("dedupeRatio")
    if dedupl_ratio_str is not None:
        dedupl_ratio = float(dedupl_ratio_str)
        yield 0, "Dedup ratio: %.2f" % dedupl_ratio, [("dedup_rate", dedupl_ratio)]
