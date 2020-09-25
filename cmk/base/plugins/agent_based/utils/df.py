#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Any,
    List,
    Tuple,
    Dict,
    Optional,
)
import fnmatch
from cmk.base.check_api import savefloat
from cmk.utils.render import fmt_number_with_precision
from .size_trend import size_trend
from ..agent_based_api.v1 import (
    render,
    Metric,
    Result,
    State as state,
    check_levels,
)
from ..agent_based_api.v1.type_defs import (
    Parameters,
    ValueStore,
)

FILESYSTEM_DEFAULT_LEVELS = {
    "levels": (80.0, 90.0),  # warn/crit in percent
    "magic_normsize": 20,  # Standard size if 20 GB
    "levels_low": (50.0, 60.0),  # Never move warn level below 50% due to magic factor
    "trend_range": 24,
    "trend_perfdata": True,  # do send performance data for trends
    "show_levels": "onmagic",
    "inodes_levels": (10.0, 5.0),
    "show_inodes": "onlow",
    "show_reserved": False,
}


def get_filesystem_levels(size_gb: float, params):
    """
    >>> from pprint import pprint as pp
    >>> pp(get_filesystem_levels(1234, FILESYSTEM_DEFAULT_LEVELS))
    {'inodes_levels': (10.0, 5.0),
     'levels': (80.0, 90.0),
     'levels_low': (50.0, 60.0),
     'levels_mb': (1010892.8, 1137254.4),
     'levels_text': '(warn/crit at 80.0%/90.0%)',
     'magic_normsize': 20,
     'show_inodes': 'onlow',
     'show_levels': 'onmagic',
     'show_reserved': False,
     'trend_perfdata': True,
     'trend_range': 24}
    >>> pp(get_filesystem_levels(123, {"levels": (10,20)}))
    {'inodes_levels': (None, None),
     'levels': (10, 20),
     'levels_low': (50.0, 60.0),
     'levels_mb': (9.999999999999998, 19.999999999999996),
     'levels_text': '(warn/crit at 10.0 MiB/20.0 MiB)',
     'magic_normsize': 20,
     'show_inodes': 'onlow',
     'show_levels': 'onmagic',
     'show_reserved': False,
     'trend_perfdata': True,
     'trend_range': 24}
    """
    mega = 1024 * 1024
    giga = mega * 1024

    # Override default levels with params
    levels: Dict[str, Any] = {**FILESYSTEM_DEFAULT_LEVELS, **params}

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
        # Type-ingore: levels["levels"] was overridden by params and should be list of tuples
        for to_size, this_levels in levels["levels"]:  # type: ignore[attr-defined]
            if size_gb * giga > to_size >= found_size:
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
        levels["levels_text"] = "(%s %s/%s)" % (label, render.percent(warn_scaled),
                                                render.percent(crit_scaled))
    else:
        if warn * mega < 0 and crit * mega < 0:
            label = 'warn/crit at free space below'
            warn *= -1
            crit *= -1
        else:
            label = 'warn/crit at'
        warn_hr = render.bytes(warn * mega)
        crit_hr = render.bytes(crit * mega)
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
            # Type-ingore: levels["levels"] was overridden by params and should be list of tuples
            for to_size, this_levels in levels["inodes_levels"]:  # type: ignore[attr-defined]
                if size_gb * giga > to_size >= found_size:
                    warn, crit = this_levels
                    found_size = to_size
                    found = True
            if not found:
                warn, crit = 100.0, 100.0  # entry not found in list
        levels["inodes_levels"] = warn, crit
    else:
        levels["inodes_levels"] = (None, None)

    return levels


def mountpoints_in_group(mplist: Dict[str, Dict], patterns_include: List, patterns_exclude: List):
    matching_mountpoints = set()
    for mountpoint in mplist:
        if any(
                fnmatch.fnmatch(mountpoint, pattern_exclude)
                for pattern_exclude in patterns_exclude):
            continue
        if any(
                fnmatch.fnmatch(mountpoint, pattern_include)
                for pattern_include in patterns_include):
            matching_mountpoints.add(mountpoint)
    return matching_mountpoints


def _check_inodes(levels: Dict[str, Any], inodes_total: Optional[float],
                  inodes_avail: Optional[float]):
    """
    >>> from pprint import pprint as pp
    >>> levels={"inodes_levels":(10, 5),"show_inodes":"onproblem"}
    >>> pp(list(_check_inodes(levels, 80, 60)))
    [Result(state=<State.OK: 0>, summary='Inodes Used: 20.00 ', details='Inodes Used: 20.00 '),
     Metric('inodes_used', 20.0, levels=(70.0, 75.0), boundaries=(0.0, 80.0))]

    >>> levels["show_inodes"] = "always"
    >>> pp(list(_check_inodes(levels, 80, 20)))
    [Result(state=<State.OK: 0>, summary='Inodes Used: 60.00 , inodes available: 20.00 /25.0%', \
details='Inodes Used: 60.00 , inodes available: 20.00 /25.0%'),
     Metric('inodes_used', 60.0, levels=(70.0, 75.0), boundaries=(0.0, 80.0))]

    >>> levels["show_inodes"]="onlow"
    >>> levels["inodes_levels"]= (40, 35)
    >>> pp(list(_check_inodes(levels, 80, 20)))
    [Result(state=<State.CRIT: 2>, summary='Inodes Used: 60.00  (warn/crit at 40.00 /45.00 ), \
inodes available: 20.00 /25.0%', details='Inodes Used: 60.00  (warn/crit at 40.00 /45.00 ), \
inodes available: 20.00 /25.0%'),
     Metric('inodes_used', 60.0, levels=(40.0, 45.0), boundaries=(0.0, 80.0))]
    """
    if not inodes_total or not inodes_avail:
        return

    inodes_warn_variant, inodes_crit_variant = levels["inodes_levels"]

    if isinstance(inodes_warn_variant, int):
        # Levels in absolute numbers
        inodes_abs = (
            inodes_total - inodes_warn_variant,
            inodes_total - inodes_crit_variant,
        )
        human_readable_func = lambda x: fmt_number_with_precision(x)  # pylint: disable=unnecessary-lambda
    elif isinstance(inodes_warn_variant, float):
        # Levels in percent
        inodes_abs = (
            (100 - inodes_warn_variant) / 100.0 * inodes_total,
            (100 - inodes_crit_variant) / 100.0 * inodes_total,
        )
        human_readable_func = lambda x: render.percent(100.0 * x / inodes_total
                                                      )  # type: ignore[misc]
    else:
        inodes_abs = None  # type: ignore[assignment] # check_levels excepts levels as tuple or None
        human_readable_func = fmt_number_with_precision

    inode_results = check_levels(
        value=inodes_total - inodes_avail,
        levels_upper=inodes_abs,
        metric_name='inodes_used',
        render_func=human_readable_func,
        boundaries=(0, inodes_total),
        label="Inodes Used",
    )

    # Only show inodes if they are at less then 50%
    show_inodes = levels["show_inodes"]
    inodes_avail_perc = 100.0 * inodes_avail / inodes_total
    for inode_result in inode_results:

        # Modify yielded summary if it is a Result (and not a Metric, which has no summary)
        if isinstance(inode_result, Result):
            infotext = (
                "%s, inodes available: %s/%s" % (
                    inode_result.summary,
                    fmt_number_with_precision(inodes_avail),
                    render.percent(inodes_avail_perc),
                )  #
                if any((
                    show_inodes == "always",
                    show_inodes == "onlow" and
                    (int(inode_result.state) > int(state.OK) or inodes_avail_perc < 50),
                    show_inodes == "onproblem" and int(inode_result.state) > int(state.OK),
                )) else inode_result.summary)
            yield Result(state=inode_result.state, summary=infotext)
        else:
            yield inode_result


def df_check_filesystem_single(
    value_store: ValueStore,
    check: str,
    mountpoint: str,
    size_mb: float,
    avail_mb: float,
    reserved_mb: float,
    inodes_total: Optional[float],
    inodes_avail: Optional[float],
    params: Parameters,
    this_time=None,
):
    if size_mb == 0:
        yield Result(state=state.WARN, summary="Size of filesystem is 0 MB")
        return

    # params might still be a tuple
    show_levels, subtract_reserved, show_reserved = ((params.get("show_levels", False),
                                                      params.get("subtract_reserved", False) and
                                                      reserved_mb > 0,
                                                      params.get("show_reserved") and
                                                      reserved_mb > 0))

    used_mb = size_mb - avail_mb
    used_max = size_mb
    if subtract_reserved:
        used_mb -= reserved_mb
        used_max -= reserved_mb

    # Get warning and critical levels already with 'magic factor' applied
    levels = get_filesystem_levels(size_mb / 1024., params)
    warn_mb, crit_mb = levels["levels_mb"]

    used_hr = render.bytes(used_mb * 1024**2)
    used_max_hr = render.bytes(used_max * 1024**2)
    used_perc_hr = render.percent(100.0 * used_mb / used_max)

    # If both numbers end with the same unit, then drop the first one
    if used_hr[-2:] == used_max_hr[-2:]:
        used_hr = used_hr[:-3]

    if warn_mb < 0.0:
        # Negative levels, so user configured thresholds based on space left. Calculate the
        # upper thresholds based on the size of the filesystem
        crit_mb = used_max + crit_mb
        warn_mb = used_max + warn_mb

    status = state.CRIT if used_mb >= crit_mb else state.WARN if used_mb >= warn_mb else state.OK
    yield Metric("fs_used", used_mb, levels=(warn_mb, crit_mb), boundaries=(0, size_mb))
    yield Metric("fs_size", size_mb)
    yield Metric("fs_used_percent", 100.0 * used_mb / size_mb)

    # Expand infotext according to current params
    infotext = ["%s used (%s of %s)" % (used_perc_hr, used_hr, used_max_hr)]
    if (show_levels == "always" or  #
        (show_levels == "onproblem" and status is not state.OK) or  #
        (show_levels == "onmagic" and (status is not state.OK or levels.get("magic", 1.0) != 1.0))):
        infotext.append(levels["levels_text"])
    yield Result(state=status, summary=", ".join(infotext))

    if show_reserved:
        reserved_perc_hr = render.percent(100.0 * reserved_mb / size_mb)
        reserved_hr = render.bytes(reserved_mb * 1024**2)
        yield Result(
            state=status,
            summary="additionally reserved for root: %s" % reserved_hr  #
            if subtract_reserved else  #
            "therein reserved for root: %s (%s)" % (reserved_perc_hr, reserved_hr))

    if subtract_reserved:
        yield Metric("fs_free", avail_mb, boundaries=(0, size_mb))

    if subtract_reserved or show_reserved:
        yield Metric("reserved", reserved_mb)

    yield from size_trend(
        value_store=value_store,
        check=check,
        item=mountpoint,
        resource="disk",
        levels=levels,
        used_mb=used_mb,
        size_mb=size_mb,
        timestamp=this_time,
    )

    yield from _check_inodes(levels, inodes_total, inodes_avail)


def df_check_filesystem_list(
    value_store: ValueStore,
    check: str,
    item: str,
    params: Parameters,
    fslist_blocks: List[Tuple[str, float, float, float]],
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
        data, inodes_data = blocks_info.get(item, {}), inodes_info.get(item, {})
        yield from df_check_filesystem_single(
            value_store,
            check,
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
        yield Result(state=state.UNKNOWN, summary="No filesystem matching the patterns")
        return

    total_size_mb = group_sum("size_mb", blocks_info, matching_mountpoints)
    total_avail_mb = group_sum("avail_mb", blocks_info, matching_mountpoints)
    total_reserved_mb = group_sum("reserved_mb", blocks_info, matching_mountpoints)

    total_inodes = group_sum("inodes_total", inodes_info, matching_mountpoints)
    total_inodes_avail = group_sum("inodes_avail", inodes_info, matching_mountpoints)

    yield from df_check_filesystem_single(
        value_store,
        check,
        item,
        total_size_mb,
        total_avail_mb,
        total_reserved_mb,
        total_inodes,
        total_inodes_avail,
        params,
        this_time,
    )

    yield Result(state=state.OK, summary="%d filesystems" % len(matching_mountpoints))
