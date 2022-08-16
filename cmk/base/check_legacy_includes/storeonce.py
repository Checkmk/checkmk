#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Final, Iterable, Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import render
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .df import df_check_filesystem_list

CheckResult = Iterable[tuple[int, str, list] | tuple[int, str]]
SectionServiceSets = Mapping[str, Mapping[str, str]]

STATE_MAP: Final = {
    "0": 3,  # Unknown
    "1": 0,  # OK
    "2": 0,  # Information
    "3": 1,  # Warning
    "4": 2,  # Critical
}


def parse_storeonce_servicesets(string_table: StringTable) -> SectionServiceSets:
    parsed: dict[str, dict[str, str]] = {}
    for line in string_table:
        if line[0].startswith("["):
            item = line[0]
            parsed[item] = {}
        else:
            parsed[item][line[0]] = line[1]
    return parsed


def _get_storeonce_space_values(
    values: Mapping[str, str | int | float], type_: str
) -> tuple[float, float, float]:
    key = "%s in bytes" % type_
    if key in values:
        return float(values[key]), 0.0, 0.0

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


def check_storeonce_space(
    item: str, params: Mapping[str, Any], values: Mapping[str, str | int | float]
) -> CheckResult:
    total_bytes, cloud_bytes, local_bytes = _get_storeonce_space_values(values, "Capacity")
    free_bytes, free_cloud_bytes, free_local_bytes = _get_storeonce_space_values(
        values, "Free Space"
    )

    factor = 1024 * 1024
    yield df_check_filesystem_list(
        item, params, [(item, total_bytes / factor, free_bytes / factor, 0)]
    )

    if cloud_bytes:
        yield 0, "Total cloud: %s" % render.bytes(cloud_bytes)
    if local_bytes:
        yield 0, "Total local: %s" % render.bytes(local_bytes)
    if free_cloud_bytes:
        yield 0, "Free cloud: %s" % render.bytes(free_cloud_bytes)
    if free_local_bytes:
        yield 0, "Free local: %s" % render.bytes(free_local_bytes)

    dedupl_ratio_str = values.get("Deduplication Ratio") or values.get("dedupeRatio")
    if dedupl_ratio_str is not None:
        dedupl_ratio = float(dedupl_ratio_str)
        yield 0, "Dedup ratio: %.2f" % dedupl_ratio, [("dedup_rate", dedupl_ratio)]
