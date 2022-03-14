#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=chained-comparison,unused-import

from typing import Any, Dict, List

from cmk.base.api.agent_based.checking_classes import Metric, Result
from cmk.base.check_api import get_bytes_human_readable, get_percent_human_readable
from cmk.base.config import Ruleset
from cmk.base.plugins.agent_based.utils.df import _check_inodes, FILESYSTEM_DEFAULT_LEVELS
from cmk.base.plugins.agent_based.utils.df import get_filesystem_levels as _get_filesystem_levels
from cmk.base.plugins.agent_based.utils.df import mountpoints_in_group

from .size_trend import size_trend  # type: ignore[attr-defined]

# Common include file for all filesystem checks (df, df_netapp, hr_fs, ...)

# Settings for filesystem checks (df, df_vms, df_netapp and maybe others)
filesystem_levels: List[Any] = []  # obsolete. Just here to check config and warn if changed
filesystem_default_levels: Dict[str, Any] = {}  # can also be dropped some day in future

# Filesystems to ignore. They should not be sent by agent anyway and
# will indeed not be sent on Linux beginning with 1.6.0
# TODO: Check other agents
inventory_df_exclude_mountpoints = ["/dev"]

# Grouping of filesystems into groups that are monitored as one entity
# Example:
# filesystem_groups = [
#     ( [ ( "Storage pool", "/data/pool*" ) ], [ 'linux', 'prod' ], ALL_HOSTS ),
#     ( [ ( "Backup space 1", "/usr/backup/*.xyz" ),
#         ( "Backup space 2", "/usr/backup2/*.xyz" ) ], ALL_HOSTS ),
# ]
filesystem_groups: Ruleset = []

# Users might have set filesystem_default_levels to old format like (80, 90)

# needed by df, df_netapp and vms_df and maybe others in future:
# compute warning and critical levels. Takes into account the size of
# the filesystem and the magic number. Since the size is only known at
# check time this function's result cannot be precompiled.


def _get_update_from_user_config_default_levels(
    user_default_levels,
    convert_legacy_levels,
):
    # convert default levels to dictionary. This is in order support
    # old style levels like (80, 90)
    if isinstance(user_default_levels, dict):
        fs_default_levels = user_default_levels.copy()
        fs_levels = fs_default_levels.get("levels")
        if fs_levels:
            fs_default_levels["levels"] = convert_legacy_levels(fs_levels)
        return fs_default_levels

    return {
        "levels": convert_legacy_levels(user_default_levels[:2]),
        "magic": user_default_levels[2] if len(user_default_levels) >= 3 else None,
    }


def _get_update_from_params(params):
    if isinstance(params, dict):
        # If params is a dictionary, make that override the default values
        return params

    # simple format - explicitely override levels and magic
    update_params = {"levels": (float(params[0]), float(params[1]))}
    if len(params) >= 3:
        update_params["magic"] = params[2]
    return update_params


def get_filesystem_levels(mountpoint, size_gb, params):
    """Just a wrapper for the migrated version"""

    def convert_legacy_levels(value):
        if isinstance(params, tuple) or not params.get("flex_levels"):
            return tuple(map(float, value))
        return value

    update_params = {
        **_get_update_from_user_config_default_levels(
            filesystem_default_levels,
            convert_legacy_levels,
        ),
        **_get_update_from_params(params),
    }

    return _get_filesystem_levels(size_gb, update_params)


# ==================================================================================================
# THIS FUNCTION DEFINED HERE IS IN THE PROCESS OF OR HAS ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FUNCTION ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/df.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO TIMI BEFORE DOING
# ANYTHING ELSE.
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
# cmk/base/plugins/agent_based/utils/df.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO TIMI BEFORE DOING
# ANYTHING ELSE.
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
        yield 1, "Size of filesystem is 0 MB", []
        return

    # params might still be a tuple
    show_levels, subtract_reserved, show_reserved = (
        (
            params.get("show_levels", False),
            params.get("subtract_reserved", False) and reserved_mb > 0,
            params.get("show_reserved") and reserved_mb > 0,
        )
        # params might still be a tuple
        if isinstance(params, dict)
        else (False, False, False)
    )

    used_mb = size_mb - avail_mb
    used_max = size_mb
    if subtract_reserved:
        used_mb -= reserved_mb
        used_max -= reserved_mb

    # Get warning and critical levels already with 'magic factor' applied
    levels = get_filesystem_levels(mountpoint, size_mb / 1024.0, params)
    warn_mb, crit_mb = levels["levels_mb"]

    used_hr = get_bytes_human_readable(used_mb * 1024**2)
    used_max_hr = get_bytes_human_readable(used_max * 1024**2)
    used_perc_hr = get_percent_human_readable(100.0 * used_mb / used_max)

    # If both numbers end with the same unit, then drop the first one
    if used_hr[-2:] == used_max_hr[-2:]:
        used_hr = used_hr[:-3]

    infotext = ["%s used (%s of %s)" % (used_perc_hr, used_hr, used_max_hr)]

    if warn_mb < 0.0:
        # Negative levels, so user configured thresholds based on space left. Calculate the
        # upper thresholds based on the size of the filesystem
        crit_mb = used_max + crit_mb
        warn_mb = used_max + warn_mb

    status = 2 if used_mb >= crit_mb else 1 if used_mb >= warn_mb else 0

    perfdata = [
        ("fs_used", used_mb, warn_mb, crit_mb, 0, size_mb),
        ("fs_size", size_mb),
        ("fs_used_percent", 100.0 * used_mb / size_mb),
    ]

    if (
        show_levels == "always"
        or (show_levels == "onproblem" and status > 0)  #
        or (show_levels == "onmagic" and (status > 0 or levels.get("magic", 1.0) != 1.0))  #
    ):
        infotext.append(levels["levels_text"])

    if show_reserved:
        reserved_perc_hr = get_percent_human_readable(100.0 * reserved_mb / size_mb)
        reserved_hr = get_bytes_human_readable(reserved_mb * 1024**2)
        infotext.append(
            "additionally reserved for root: %s" % reserved_hr  #
            if subtract_reserved
            else "therein reserved for root: %s (%s)" % (reserved_perc_hr, reserved_hr)  #
        )

    if subtract_reserved:
        perfdata.append(("fs_free", avail_mb, None, None, 0, size_mb))

    if subtract_reserved or show_reserved:
        perfdata.append(("reserved", reserved_mb))

    yield status, ", ".join(infotext).replace("), (", ", "), perfdata

    if levels.get("trend_range"):
        trend_state, trend_text, trend_perf = size_trend(
            "df",
            mountpoint,
            "disk",
            levels,
            used_mb,
            size_mb,
            this_time,
        )
        # Todo(frans): Return value from size_trend() can be empty but we must yield a valid result
        # - as soon as we can 'yield from' size_trend we do not have to check any more
        if trend_state or trend_text or trend_perf:
            yield trend_state, trend_text.strip(" ,"), trend_perf or []

    if not inodes_total or not inodes_avail:
        return

    metric, result = _check_inodes(levels, inodes_total, inodes_avail)
    assert isinstance(metric, Metric)
    assert isinstance(result, Result)
    yield int(result.state), result.summary, [
        (metric.name, metric.value) + metric.levels + metric.boundaries
    ]


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
