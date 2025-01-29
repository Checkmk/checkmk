#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any, Final

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckResult, get_value_store, render, Result, State, StringTable

from .df import df_check_filesystem_list

SectionServiceSets = Mapping[str, Mapping[str, str]]

STATE_MAP: Final = {
    "0": State.UNKNOWN,  # Unknown
    "1": State.OK,  # OK
    "2": State.OK,  # Information
    "3": State.WARN,  # Warning
    "4": State.CRIT,  # Critical
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
    item: str, params: Mapping[str, Any], section: Mapping[str, str | int | float]
) -> CheckResult:
    total_bytes, cloud_bytes, local_bytes = _get_storeonce_space_values(section, "Capacity")
    free_bytes, free_cloud_bytes, free_local_bytes = _get_storeonce_space_values(
        section, "Free Space"
    )

    factor = 1024 * 1024
    yield from df_check_filesystem_list(
        get_value_store(), item, params, [(item, total_bytes / factor, free_bytes / factor, 0)]
    )

    if cloud_bytes:
        yield Result(state=State.OK, summary="Total cloud: %s" % render.bytes(cloud_bytes))
    if local_bytes:
        yield Result(state=State.OK, summary="Total local: %s" % render.bytes(local_bytes))
    if free_cloud_bytes:
        yield Result(state=State.OK, summary="Free cloud: %s" % render.bytes(free_cloud_bytes))
    if free_local_bytes:
        yield Result(state=State.OK, summary="Free local: %s" % render.bytes(free_local_bytes))

    dedupl_ratio_str = section.get("Deduplication Ratio") or section.get("dedupeRatio")
    if dedupl_ratio_str is not None:
        yield from check_levels_v1(
            float(dedupl_ratio_str), metric_name="dedup_rate", label="Dedup ratio"
        )
