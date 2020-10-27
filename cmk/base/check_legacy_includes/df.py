#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
# pylint: disable=chained-comparison

from typing import Dict, List, Tuple
from cmk.base.config import factory_settings
from cmk.base.check_api import get_number_with_precision

from cmk.base.check_api import host_name
from cmk.base.check_api import get_bytes_human_readable
from cmk.base.check_api import savefloat
from cmk.base.check_api import host_extra_conf
from cmk.base.check_api import get_percent_human_readable
from cmk.base.check_api import check_levels

from cmk.base.plugins.agent_based.utils.df import (
    mountpoints_in_group,
    FILESYSTEM_DEFAULT_LEVELS as _FILESYSTEM_DEFAULT_LEVELS,
    ungrouped_mountpoints_and_groups,
)

from .size_trend import size_trend

# Common include file for all filesystem checks (df, df_netapp, hr_fs, ...)

# Settings for filesystem checks (df, df_vms, df_netapp and maybe others)
filesystem_levels = []  # obsolete. Just here to check config and warn if changed
filesystem_default_levels = {}  # can also be dropped some day in future

# Filesystems to ignore. They should not be sent by agent anyway and
# will indeed not be sent on Linux beginning with 1.6.0
# TODO: Check other agents
inventory_df_exclude_mountpoints = ['/dev']

# Grouping of filesystems into groups that are monitored as one entity
# Example:
# filesystem_groups = [
#     ( [ ( "Storage pool", "/data/pool*" ) ], [ 'linux', 'prod' ], ALL_HOSTS ),
#     ( [ ( "Backup space 1", "/usr/backup/*.xyz" ),
#         ( "Backup space 2", "/usr/backup2/*.xyz" ) ], ALL_HOSTS ),
# ]
filesystem_groups = []

factory_settings["filesystem_default_levels"] = _FILESYSTEM_DEFAULT_LEVELS


def transform_filesystem_groups(groups):
    """
    Old format:
    [(group_name, include_pattern), (group_name, include_pattern), ...]
    New format:
    [{group_name: name,
      patterns_include: [include_pattern, include_pattern, ...],
      patterns_exclude: [exclude_pattern, exclude_pattern, ...]},
     {group_name: name,
      patterns_include: [include_pattern, include_pattern, ...],
      patterns_exclude: [exclude_pattern, exclude_pattern, ...]},
     ...]
    """
    if not groups or isinstance(groups[0], dict):
        yield from groups
        return
    for group_name, include_pattern in groups:
        yield {
            'group_name': group_name,
            'patterns_include': [include_pattern],
            'patterns_exclude': [],
        }


def df_inventory(mplist):
    group_patterns: Dict[str, Tuple[List[str], List[str]]] = {}
    for groups in host_extra_conf(host_name(), filesystem_groups):
        for group in transform_filesystem_groups(groups):
            grouping_entry = group_patterns.setdefault(group['group_name'], ([], []))
            grouping_entry[0].extend(group['patterns_include'])
            grouping_entry[1].extend(group['patterns_exclude'])

    ungrouped_mountpoints, groups = ungrouped_mountpoints_and_groups(mplist, group_patterns)

    return [(mp, {}) for mp in ungrouped_mountpoints] \
            + [(group, {"patterns": group_patterns[group]}) for group in groups]


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


# ==================================================================================================
# THIS FUNCTION DEFINED HERE IS IN THE PROCESS OF OR HAS ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FUNCTION ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/df.py
# IF YOU CANNOT FIND THE MIGRATED COUNTERPART OF A FUNCTION, PLEASE TALK TO TIMI BEFORE DOING
# ANYTHING ELSE.
# ==================================================================================================
def get_filesystem_levels(mountpoint, size_gb, params):
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

    mega = 1024 * 1024
    giga = mega * 1024

    # Override default levels with params
    levels = {**_FILESYSTEM_DEFAULT_LEVELS, **update_params}

    # Determine real warn, crit levels
    if isinstance(levels["levels"], tuple):
        warn, crit = levels["levels"]
    else:
        # A list of levels. Choose the correct one depending on the
        # size of the current filesystem. We do not make the first
        # rule match, but that with the largest size_gb. That way
        # the order of the entries is not important.
        found = False
        found_size = 0
        for to_size, this_levels in levels["levels"]:
            if size_gb * giga > to_size and to_size >= found_size:
                warn, crit = this_levels
                found_size = to_size
                found = True
        if not found:
            warn, crit = 100.0, 100.0  # entry not found in list

    # Take into account magic scaling factor (third optional argument
    # in check params). A factor of 1.0 changes nothing. Factor should
    # be > 0 and <= 1. A smaller factor raises levels for big file systems
    # bigger than 100 GB and lowers it for file systems smaller than 100 GB.
    # Please run df_magic_factor.py to understand how it works.

    magic = levels.get("magic")
    # We need a way to disable the magic factor so check
    # if magic not 1.0
    if magic and magic != 1.0:
        # convert warn/crit to percentage
        if not isinstance(warn, float):
            warn = savefloat(warn * mega / float(size_gb * giga)) * 100
        if not isinstance(crit, float):
            crit = savefloat(crit * mega / float(size_gb * giga)) * 100

        normsize = levels["magic_normsize"]
        hgb_size = size_gb / float(normsize)
        felt_size = hgb_size**magic
        scale = felt_size / hgb_size
        warn_scaled = 100 - ((100 - warn) * scale)
        crit_scaled = 100 - ((100 - crit) * scale)

        # Make sure, levels do never get too low due to magic factor
        lowest_warning_level, lowest_critical_level = levels["levels_low"]
        if warn_scaled < lowest_warning_level:
            warn_scaled = lowest_warning_level
        if crit_scaled < lowest_critical_level:
            crit_scaled = lowest_critical_level
    else:
        if not isinstance(warn, float):
            warn_scaled = savefloat(warn * mega / float(size_gb * giga)) * 100
        else:
            warn_scaled = warn

        if not isinstance(crit, float):
            crit_scaled = savefloat(crit * mega / float(size_gb * giga)) * 100
        else:
            crit_scaled = crit

    size_mb = size_gb * 1024
    warn_mb = savefloat(size_mb * warn_scaled / 100)
    crit_mb = savefloat(size_mb * crit_scaled / 100)
    levels["levels_mb"] = (warn_mb, crit_mb)
    if isinstance(warn, float):
        if warn_scaled < 0 and crit_scaled < 0:
            label = 'warn/crit at free space below'
            warn_scaled *= -1
            crit_scaled *= -1
        else:
            label = 'warn/crit at'
        levels["levels_text"] = "(%s %s/%s)" % (label, get_percent_human_readable(warn_scaled),
                                                get_percent_human_readable(crit_scaled))
    else:
        if warn * mega < 0 and crit * mega < 0:
            label = 'warn/crit at free space below'
            warn *= -1
            crit *= -1
        else:
            label = 'warn/crit at'
        warn_hr = get_bytes_human_readable(warn * mega)
        crit_hr = get_bytes_human_readable(crit * mega)
        levels["levels_text"] = "(%s %s/%s)" % (label, warn_hr, crit_hr)

    inodes_levels = params.get("inodes_levels")
    if inodes_levels:
        if isinstance(levels["inodes_levels"], tuple):
            warn, crit = levels["inodes_levels"]
        else:
            # A list of inode levels. Choose the correct one depending on the
            # size of the current filesystem. We do not make the first
            # rule match, but that with the largest size_gb. That way
            # the order of the entries is not important.
            found = False
            found_size = 0
            for to_size, this_levels in levels["inodes_levels"]:
                if size_gb * giga > to_size and to_size >= found_size:
                    warn, crit = this_levels
                    found_size = to_size
                    found = True
            if not found:
                warn, crit = 100.0, 100.0  # entry not found in list
        levels["inodes_levels"] = warn, crit
    else:
        levels["inodes_levels"] = (None, None)

    return levels


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
        return sum(block_info[metric_name]  #
                   for (mp, block_info) in info.items()  #
                   if mp in mountpoints_group)

    # Translate lists of tuples into convienient dicts
    blocks_info = {
        mountp: {
            "size_mb": size_mb,
            "avail_mb": avail_mb,
            "reserved_mb": reserved_mb,
        } for (mountp, size_mb, avail_mb, reserved_mb) in (fslist_blocks or [])
    }
    inodes_info = {
        mountp: {
            "inodes_total": inodes_total,
            "inodes_avail": inodes_avail,
        } for (mountp, inodes_total, inodes_avail) in (fslist_inodes or [])
    }

    if "patterns" not in params:
        # No patterns provided - return result for mountpoint defined in @item
        if item not in blocks_info:
            return
        data, inodes_data = blocks_info.get(item), inodes_info.get(item, {})
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
def _check_inodes(levels, inodes_total, inodes_avail):
    if not inodes_total:
        return

    inodes_warn_variant, inodes_crit_variant = levels["inodes_levels"]
    inodes_warn_abs, inodes_crit_abs, human_readable_func = (
        # Levels in absolute numbers
        (
            inodes_total - inodes_warn_variant,
            inodes_total - inodes_crit_variant,
            get_number_with_precision,
        ) if isinstance(inodes_warn_variant, int) else
        # Levels in percent
        (
            (100 - inodes_warn_variant) / 100.0 * inodes_total,
            (100 - inodes_crit_variant) / 100.0 * inodes_total,
            lambda x: get_percent_human_readable(100.0 * x / inodes_total),
        ) if isinstance(inodes_warn_variant, float) else  #
        (None, None, get_number_with_precision))

    inode_status, inode_text, inode_perf = check_levels(
        inodes_total - inodes_avail,
        'inodes_used',
        (inodes_warn_abs, inodes_crit_abs),
        boundaries=(0, inodes_total),
        human_readable_func=human_readable_func,
        infoname="Inodes Used",
    )

    # Only show inodes if they are at less then 50%
    show_inodes = levels["show_inodes"]
    inodes_avail_perc = 100.0 * inodes_avail / inodes_total
    infotext = (
        "%s, inodes available: %s/%s" % (
            inode_text,
            get_number_with_precision(inodes_avail),
            get_percent_human_readable(inodes_avail_perc),
        )  #
        if any((
            show_inodes == "always",
            show_inodes == "onlow" and (inode_status or inodes_avail_perc < 50),
            show_inodes == "onproblem" and inode_status,
        )) else "")

    yield inode_status, infotext, inode_perf


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
        (params.get("show_levels", False),
         params.get("subtract_reserved", False) and reserved_mb > 0,
         params.get("show_reserved") and reserved_mb > 0)
        # params might still be a tuple
        if isinstance(params, dict) else (False, False, False))

    used_mb = size_mb - avail_mb
    used_max = size_mb
    if subtract_reserved:
        used_mb -= reserved_mb
        used_max -= reserved_mb

    # Get warning and critical levels already with 'magic factor' applied
    levels = get_filesystem_levels(mountpoint, size_mb / 1024., params)
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

    perfdata = [("fs_used", used_mb, warn_mb, crit_mb, 0, size_mb), ('fs_size', size_mb),
                ("fs_used_percent", 100.0 * used_mb / size_mb)]

    if (show_levels == "always" or  #
        (show_levels == "onproblem" and status > 0) or  #
        (show_levels == "onmagic" and (status > 0 or levels.get("magic", 1.0) != 1.0))):
        infotext.append(levels["levels_text"])

    if show_reserved:
        reserved_perc_hr = get_percent_human_readable(100.0 * reserved_mb / size_mb)
        reserved_hr = get_bytes_human_readable(reserved_mb * 1024**2)
        infotext.append("additionally reserved for root: %s" % reserved_hr  #
                        if subtract_reserved else  #
                        "therein reserved for root: %s (%s)" % (reserved_perc_hr, reserved_hr))

    if subtract_reserved:
        perfdata.append(("fs_free", avail_mb, None, None, 0, size_mb))

    if subtract_reserved or show_reserved:
        perfdata.append(("reserved", reserved_mb))

    yield status, ", ".join(infotext), perfdata

    if levels.get("trend_range"):
        trend_state, trend_text, trend_perf = size_trend(
            'df',
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

    yield from _check_inodes(levels, inodes_total, inodes_avail)


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
