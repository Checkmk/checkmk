#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.agent_based.v2 import Metric, render, Result, State
from cmk.plugins.lib.df import check_filesystem_levels, check_inodes
from cmk.plugins.lib.df import (
    FILESYSTEM_DEFAULT_LEVELS as FILESYSTEM_DEFAULT_LEVELS,  # ruff: ignore[unused-import]
)
from cmk.plugins.lib.df import (
    FILESYSTEM_DEFAULT_PARAMS as FILESYSTEM_DEFAULT_PARAMS,  # ruff: ignore[unused-import]
)
from cmk.plugins.lib.df import (
    INODES_DEFAULT_PARAMS as INODES_DEFAULT_PARAMS,  # ruff: ignore[unused-import]
)
from cmk.plugins.lib.df import mountpoints_in_group as mountpoints_in_group
from cmk.plugins.lib.df import (
    TREND_DEFAULT_PARAMS as TREND_DEFAULT_PARAMS,  # ruff: ignore[unused-import]
)

from .size_trend import size_trend

# Common include file for all filesystem checks (df, df_netapp, hr_fs, ...)


# ==================================================================================================
# THIS FUNCTION DEFINED HERE IS IN THE PROCESS OF OR HAS ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FUNCTION ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk.plugins.lib/df.py
# ==================================================================================================
def df_check_filesystem_list_coroutine(
    item,
    params,
    fslist_blocks,
    fslist_inodes=None,
    this_time=None,
):
    """Wrapper for `df_check_filesystem_single` supporting groups"""

    def group_sum(metric_name, info, mountpoints_group):
        """Calculate sum of named values for matching mount points"""
        return sum(
            block_info[metric_name]  #
            for (mp, block_info) in info.items()  #
            if mp in mountpoints_group
        )

    # Translate lists of tuples into convienient dicts
    blocks_info = {
        mountp: {
            "size_mb": size_mb,
            "avail_mb": avail_mb,
            "reserved_mb": reserved_mb,
        }
        for (mountp, size_mb, avail_mb, reserved_mb) in (fslist_blocks or [])
    }
    inodes_info = {
        mountp: {
            "inodes_total": inodes_total,
            "inodes_avail": inodes_avail,
        }
        for (mountp, inodes_total, inodes_avail) in (fslist_inodes or [])
    }

    if "patterns" not in params:
        # No patterns provided - return result for mountpoint defined in @item
        if item not in blocks_info:
            return
        data, inodes_data = blocks_info.get(item), inodes_info.get(item, {})
        assert data is not None
        yield from df_check_filesystem_single_coroutine(
            item,
            data["size_mb"],
            data["avail_mb"],
            data["reserved_mb"],
            inodes_data.get("inodes_total"),
            inodes_data.get("inodes_avail"),
            params,
            this_time,
        )
        return

    matching_mountpoints = mountpoints_in_group(blocks_info, *params["patterns"])
    if not matching_mountpoints:
        yield 3, "No filesystem matching the patterns", []
        return

    total_size_mb = group_sum("size_mb", blocks_info, matching_mountpoints)
    total_avail_mb = group_sum("avail_mb", blocks_info, matching_mountpoints)
    total_reserved_mb = group_sum("reserved_mb", blocks_info, matching_mountpoints)

    total_inodes = group_sum("inodes_total", inodes_info, matching_mountpoints)
    total_inodes_avail = group_sum("inodes_avail", inodes_info, matching_mountpoints)

    yield from df_check_filesystem_single_coroutine(
        item,
        total_size_mb,
        total_avail_mb,
        total_reserved_mb,
        total_inodes,
        total_inodes_avail,
        params,
        this_time,
    )

    yield 0, "%d filesystems" % len(matching_mountpoints), []


# ==================================================================================================
# THIS FUNCTION DEFINED HERE IS IN THE PROCESS OF OR HAS ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FUNCTION ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk.plugins.lib/df.py
# ==================================================================================================
def df_check_filesystem_single_coroutine(
    mountpoint,
    size_mb,
    avail_mb,
    reserved_mb,
    inodes_total,
    inodes_avail,
    params,
    this_time=None,
):
    if size_mb == 0:
        yield 1, "Size of filesystem is 0 B", []
        return

    # params might still be a tuple
    show_levels: Literal["onmagic", "always", "onproblem"]
    show_levels, subtract_reserved, show_reserved = (
        (
            params.get("show_levels", "onproblem"),
            params.get("subtract_reserved", False) and reserved_mb > 0,
            params.get("show_reserved") and reserved_mb > 0,
        )
        # params might still be a tuple  # (mo): I don't think so.
        if isinstance(params, dict)
        else ("onproblem", False, False)
    )

    used_mb = size_mb - avail_mb
    used_max = size_mb
    if subtract_reserved:
        used_mb -= reserved_mb
        used_max -= reserved_mb

    state = State.OK
    infotext = []
    perfdata: list[tuple[str, float, float | None, float | None, float | None, float | None]] = []
    for result in check_filesystem_levels(
        size_mb, used_max, avail_mb, used_mb, params, show_levels
    ):
        if isinstance(result, Result):
            state = State.worst(state, result.state)
            infotext.append(result.summary)
        elif isinstance(result, Metric):
            name = result.name
            value = result.value
            if hasattr(result, "levels"):
                perflevels = result.levels
            else:
                perflevels = None, None
            if hasattr(result, "boundaries"):
                perfboundaries = result.boundaries
            else:
                perfboundaries = None, None
            perfdata.append((name, value, *perflevels, *perfboundaries))

    perfdata.append(("fs_size", size_mb, None, None, 0, None))

    if show_reserved:
        reserved_perc_hr = render.percent(100.0 * reserved_mb / size_mb)
        reserved_hr = render.bytes(reserved_mb * 1024**2)
        infotext.append(
            "additionally reserved for root: %s" % reserved_hr  #
            if subtract_reserved
            else f"therein reserved for root: {reserved_perc_hr} ({reserved_hr})"  #
        )

    if subtract_reserved or show_reserved:
        perfdata.append(("reserved", reserved_mb, None, None, None, None))

    yield int(state), ", ".join(infotext), perfdata

    if params.get("trend_range"):
        trend_state, trend_text, trend_perf = size_trend(
            "df",
            mountpoint,
            "disk",
            params,
            used_mb,
            size_mb,
            this_time,
        )
        # Todo(frans): Return value from size_trend() can be empty but we must yield a valid result
        # - as soon as we can 'yield from' size_trend we do not have to check any more
        if trend_state or trend_text or trend_perf:
            yield trend_state, trend_text.strip(" ,"), trend_perf or []

    if not inodes_total or inodes_avail is None:
        return

    metric, result = check_inodes(params, inodes_total, inodes_avail)
    assert isinstance(metric, Metric)
    assert isinstance(result, Result)
    yield (
        int(result.state),
        result.summary,
        [(metric.name, metric.value) + metric.levels + metric.boundaries],
    )


def _aggregate(generator):
    """Deprecated: used only to mimic old non-coroutine functions - don't use"""

    def wrapped(*args, **kwargs):
        try:
            state, text, perfdata = tuple(zip(*generator(*args, **kwargs)))
        except ValueError:
            # BasicResult needs None - defaulting to ((), (), ()) doesn't help
            return None
        return max(state), ", ".join(elem.strip(" ,") for elem in text if elem), sum(perfdata, [])

    return wrapped


# Don't use df_check_filesystem_single or df_check_filesystem_list anymore
# - use the *_coroutine variants instead
df_check_filesystem_single = _aggregate(df_check_filesystem_single_coroutine)
df_check_filesystem_list = _aggregate(df_check_filesystem_list_coroutine)
