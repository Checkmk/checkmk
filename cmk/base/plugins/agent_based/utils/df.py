#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fnmatch
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Mapping,
    MutableMapping,
    NamedTuple,
    NewType,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from ..agent_based_api.v1 import check_levels, Metric, render, Result, State
from ..agent_based_api.v1.type_defs import CheckResult
from .size_trend import size_trend


class DfBlock(NamedTuple):
    device: str
    fs_type: Optional[str]
    size_mb: float
    avail_mb: float
    reserved_mb: float
    mountpoint: str
    uuid: Optional[str]


class DfInode(NamedTuple):
    device: Optional[str]
    total: int
    avail: int
    mountpoint: str
    uuid: Optional[str]


FSBlock = Tuple[str, Optional[float], Optional[float], float]
FSBlocks = Sequence[FSBlock]
BlocksSubsection = Sequence[DfBlock]
InodesSubsection = Sequence[DfInode]
Bytes = NewType("Bytes", int)
Percent = NewType("Percent", float)


class RenderOptions(Enum):
    bytes_ = "bytes"
    percent = "percent"


class LevelsFreeSpace(NamedTuple):
    warn_percent: Percent
    crit_percent: Percent
    warn_absolute: Bytes
    crit_absolute: Bytes
    render_as: RenderOptions


class LevelsUsedSpace(NamedTuple):
    warn_percent: Percent
    crit_percent: Percent
    warn_absolute: Bytes
    crit_absolute: Bytes
    render_as: RenderOptions


FilesystemLevels = LevelsFreeSpace | LevelsUsedSpace


DfSection = tuple[BlocksSubsection, InodesSubsection]


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


def _determine_levels_for_filesystem(levels: list, filesystem_size: Bytes) -> Tuple[Any, Any]:
    # A list of levels. Choose the correct one depending on the
    # size of the current filesystem. We do not make the first
    # rule match, but that with the largest size_gb. That way
    # the order of the entries is not important.
    found = False
    found_size = 0
    # Type-ingore: levels["levels"] was overridden by params and should be list of tuples
    for to_size, this_levels in levels:  # type: ignore[attr-defined]
        if filesystem_size > to_size >= found_size:
            warn, crit = this_levels
            found_size = to_size
            found = True
        if not found:
            warn, crit = 100.0, 100.0  # entry not found in list
    return warn, crit


def _adjust_levels(
    levels: FilesystemLevels,
    factor: float,
    filesystem_size: Bytes,
    reference_size: Bytes,
    minimum_levels: Tuple[float, float],
) -> FilesystemLevels:
    hgb_size = filesystem_size / reference_size
    felt_size = hgb_size**factor
    scale = felt_size / hgb_size
    warn_scaled = 100 - ((100 - levels.warn_percent) * scale)
    crit_scaled = 100 - ((100 - levels.crit_percent) * scale)

    # Make sure, levels do never get too low due to magic factor
    lowest_warning_level, lowest_critical_level = minimum_levels
    warn_scaled = Percent(max(warn_scaled, lowest_warning_level))
    crit_scaled = Percent(max(crit_scaled, lowest_critical_level))

    warn_scaled_absolute = _to_absolute(warn_scaled, filesystem_size)
    crit_scaled_absolute = _to_absolute(crit_scaled, filesystem_size)

    if isinstance(levels, LevelsFreeSpace):
        return LevelsFreeSpace(
            warn_percent=warn_scaled,
            crit_percent=crit_scaled,
            warn_absolute=warn_scaled_absolute,
            crit_absolute=crit_scaled_absolute,
            render_as=levels.render_as,
        )

    return LevelsUsedSpace(
        warn_percent=warn_scaled,
        crit_percent=crit_scaled,
        warn_absolute=warn_scaled_absolute,
        crit_absolute=crit_scaled_absolute,
        render_as=levels.render_as,
    )


def _check_summary_text(levels: FilesystemLevels) -> str:
    # TODO: this is the same as the functionality provided in memory.py!

    if levels.render_as is RenderOptions.percent:
        applied_levels = (
            f"{render.percent(abs(levels.warn_percent))}/{render.percent(abs(levels.crit_percent))}"
        )
    elif levels.render_as is RenderOptions.bytes_:
        applied_levels = (
            f"{render.bytes(abs(levels.warn_absolute))}/{render.bytes(abs(levels.crit_absolute))}"
        )
    else:
        raise TypeError(f"Unsupported render type: {repr(levels.render_as)}")

    if isinstance(levels, LevelsFreeSpace):
        return f"(warn/crit below {applied_levels} free)"

    return f"(warn/crit at {applied_levels} used)"


def _is_free_space_level(warn: int | float, crit: int | float) -> bool:
    """
    >>> _is_free_space_level(-1, -1)
    True
    >>> _is_free_space_level(0, 0)
    False
    >>> _is_free_space_level(1, 1)
    False
    """
    if warn < 0 and crit < 0:
        return True
    if warn >= 0 and crit >= 0:
        return False
    raise TypeError(
        f"Unable to determine whether levels are for used or free space, got {repr((warn, crit))}"
    )


def _to_absolute(level: Percent, size: Bytes) -> Bytes:
    """
    >>> _to_absolute(80.0, 200)
    160
    """
    return Bytes(int(size * (level / 100)))


def _to_percent(level: Bytes, size: Bytes) -> Percent:
    """
    >>> _to_percent(160, 200)
    80.0
    """
    return Percent((level / size) * 100.0)


def _parse_free_used_levels(levels: tuple, filesystem_size: Bytes) -> FilesystemLevels:
    warn, crit = levels
    if isinstance(warn, int) and isinstance(crit, int):
        warn_absolute = Bytes(warn * 1024 * 1024)
        crit_absolute = Bytes(crit * 1024 * 1024)
        warn_percent = _to_percent(warn_absolute, filesystem_size)
        crit_percent = _to_percent(crit_absolute, filesystem_size)
        render_as = RenderOptions.bytes_
    elif isinstance(warn, float) and isinstance(crit, float):
        warn_percent = Percent(warn)
        crit_percent = Percent(crit)
        warn_absolute = _to_absolute(warn_percent, filesystem_size)
        crit_absolute = _to_absolute(crit_percent, filesystem_size)
        render_as = RenderOptions.percent
    else:
        raise TypeError(
            "Expected tuple of int or tuple of float for filesystem levels, got {type(warn).__name__}/{type(crit).__name__}"
        )

    if _is_free_space_level(warn, crit):
        return LevelsFreeSpace(
            warn_percent=warn_percent,
            crit_percent=crit_percent,
            warn_absolute=warn_absolute,
            crit_absolute=crit_absolute,
            render_as=render_as,
        )
    return LevelsUsedSpace(
        warn_percent=warn_percent,
        crit_percent=crit_percent,
        warn_absolute=warn_absolute,
        crit_absolute=crit_absolute,
        render_as=render_as,
    )


def _parse_filesystem_levels(levels: object, filesystem_size: Bytes) -> FilesystemLevels:
    if isinstance(levels, tuple):
        return _parse_free_used_levels(levels, filesystem_size)
    if isinstance(levels, list):
        actual_levels = _determine_levels_for_filesystem(levels, filesystem_size)
        return _parse_free_used_levels(actual_levels, filesystem_size)
    raise TypeError(f"Expected list or tuple for filesystem levels, got {type(levels).__name__}")


def savefloat(raw: Any) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _ungrouped_mountpoints_and_groups(
    mount_points: Dict[str, Dict],
    group_patterns: Mapping[str, Tuple[Sequence[str], Sequence[str]]],
) -> Tuple[Set[str], Dict[str, Set[str]]]:
    ungrouped_mountpoints = set(mount_points)
    groups: Dict[str, Set[str]] = {}
    for group_name, (patterns_include, patterns_exclude) in group_patterns.items():
        mp_groups = mountpoints_in_group(mount_points, patterns_include, patterns_exclude)
        if mp_groups:
            groups[group_name] = set(mp_groups)
            ungrouped_mountpoints = ungrouped_mountpoints.difference(mp_groups)
    return ungrouped_mountpoints, groups


def get_filesystem_levels(  # pylint: disable=too-many-branches
    size_gb: float,
    params: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    >>> from pprint import pprint as pp
    >>> pp(get_filesystem_levels(1234, FILESYSTEM_DEFAULT_LEVELS))
    {'inodes_levels': (10.0, 5.0),
     'levels': (80.0, 90.0),
     'levels_low': (50.0, 60.0),
     'levels_mb': (1010892.8, 1137254.4),
     'levels_text': '(warn/crit at 80.00%/90.00% used)',
     'magic_normsize': 20,
     'show_inodes': 'onlow',
     'show_levels': 'onmagic',
     'show_reserved': False,
     'trend_perfdata': True,
     'trend_range': 24}
    >>> pp(get_filesystem_levels(123, {"levels": (10,20)}))
    {'inodes_levels': (10.0, 5.0),
     'levels': (10, 20),
     'levels_low': (50.0, 60.0),
     'levels_mb': (9.999999999999998, 19.999999999999996),
     'levels_text': '(warn/crit at 10.0 MiB/20.0 MiB used)',
     'magic_normsize': 20,
     'show_inodes': 'onlow',
     'show_levels': 'onmagic',
     'show_reserved': False,
     'trend_perfdata': True,
     'trend_range': 24}
    """
    mega = 1024 * 1024
    giga = mega * 1024
    filesystem_size = Bytes(int(size_gb * giga))

    # Override default levels with params
    levels: Dict[str, Any] = {**FILESYSTEM_DEFAULT_LEVELS, **params}

    filesystem_levels = _parse_filesystem_levels(levels["levels"], filesystem_size)

    # Take into account magic scaling factor (third optional argument
    # in check params). A factor of 1.0 changes nothing. Factor should
    # be > 0 and <= 1. A smaller factor raises levels for big file systems
    # bigger than 100 GB and lowers it for file systems smaller than 100 GB.
    # Please run df_magic_factor.py to understand how it works.

    magic = levels.get("magic")
    # We need a way to disable the magic factor so check
    # if magic not 1.0
    if magic and magic != 1.0:
        filesystem_levels = _adjust_levels(
            filesystem_levels,
            factor=magic,
            filesystem_size=filesystem_size,
            reference_size=Bytes(levels["magic_normsize"] * giga),
            minimum_levels=levels["levels_low"],
        )

    size_mb = size_gb * 1024
    warn_mb = savefloat(size_mb * filesystem_levels.warn_percent / 100)
    crit_mb = savefloat(size_mb * filesystem_levels.crit_percent / 100)
    levels["levels_mb"] = (warn_mb, crit_mb)

    levels["levels_text"] = _check_summary_text(filesystem_levels)

    if levels["inodes_levels"] is None:
        levels["inodes_levels"] = None, None

    return levels


def mountpoints_in_group(
    mplist: Dict[str, Dict],
    patterns_include: Sequence[str],
    patterns_exclude: Sequence[str],
) -> List[str]:
    """Returns a list of mount points that are in patterns_include,
    but not in patterns_exclude"""
    matching_mountpoints = []
    for mountpoint in mplist:
        if any(
            fnmatch.fnmatch(mountpoint, pattern_exclude) for pattern_exclude in patterns_exclude
        ):
            continue
        if any(
            fnmatch.fnmatch(mountpoint, pattern_include) for pattern_include in patterns_include
        ):
            if mountpoint not in matching_mountpoints:
                matching_mountpoints.append(mountpoint)
    return matching_mountpoints


def _render_integer(number: float) -> str:
    return render.filesize(number).strip(" B")


def _check_inodes(
    levels: Dict[str, Any],
    inodes_total: float,
    inodes_avail: float,
) -> Generator[Union[Metric, Result], None, None]:
    """
    >>> levels = {
    ...     "inodes_levels": (10, 5),
    ...     "show_inodes": "onproblem",
    ... }
    >>> for r in _check_inodes(levels, 80, 60): print(r)
    Metric('inodes_used', 20.0, levels=(70.0, 75.0), boundaries=(0.0, 80.0))
    Result(state=<State.OK: 0>, notice='Inodes used: 20, Inodes available: 60 (75.00%)')

    >>> levels["show_inodes"] = "always"
    >>> for r in _check_inodes(levels, 80, 20): print(r)
    Metric('inodes_used', 60.0, levels=(70.0, 75.0), boundaries=(0.0, 80.0))
    Result(state=<State.OK: 0>, summary='Inodes used: 60, Inodes available: 20 (25.00%)')

    >>> levels["show_inodes"]="onlow"
    >>> levels["inodes_levels"]= (40, 35)
    >>> for r in _check_inodes(levels, 80, 20): print(r)
    Metric('inodes_used', 60.0, levels=(40.0, 45.0), boundaries=(0.0, 80.0))
    Result(state=<State.CRIT: 2>, summary='Inodes used: 60 (warn/crit at 40/45), Inodes available: 20 (25.00%)')
    """
    inodes_warn_variant, inodes_crit_variant = levels["inodes_levels"]

    inodes_abs: Optional[Tuple[float, float]] = None
    human_readable_func: Callable[[float], str] = _render_integer
    if isinstance(inodes_warn_variant, int):
        # Levels in absolute numbers
        inodes_abs = (
            inodes_total - inodes_warn_variant,
            inodes_total - inodes_crit_variant,
        )
    elif isinstance(inodes_warn_variant, float):
        # Levels in percent
        inodes_abs = (
            (100 - inodes_warn_variant) / 100.0 * inodes_total,
            (100 - inodes_crit_variant) / 100.0 * inodes_total,
        )

        def human_readable_func(x: float) -> str:
            return render.percent(100.0 * x / inodes_total)

    inode_result, inode_metric = check_levels(
        value=inodes_total - inodes_avail,
        levels_upper=inodes_abs,
        metric_name="inodes_used",
        render_func=human_readable_func,
        boundaries=(0, inodes_total),
        label="Inodes used",
    )
    assert isinstance(inode_result, Result)
    yield inode_metric

    # Only show inodes if they are at less then 50%
    show_inodes = levels["show_inodes"]
    inodes_avail_perc = 100.0 * inodes_avail / inodes_total
    inodes_info = (
        f"{inode_result.summary}, "
        f"Inodes available: {_render_integer(inodes_avail)} ({render.percent(inodes_avail_perc)})"
    )

    if any(
        (
            show_inodes == "always",
            show_inodes == "onlow" and inodes_avail_perc < 50,
        )
    ):
        yield Result(state=inode_result.state, summary=inodes_info)
    else:
        yield Result(state=inode_result.state, notice=inodes_info)


def df_discovery(params, mplist):
    group_patterns: Dict[str, Tuple[List[str], List[str]]] = {}
    for groups in params:
        for group in groups.get("groups", []):
            grouping_entry = group_patterns.setdefault(group["group_name"], ([], []))
            grouping_entry[0].extend(group["patterns_include"])
            grouping_entry[1].extend(group["patterns_exclude"])

    ungrouped_mountpoints, groups = _ungrouped_mountpoints_and_groups(mplist, group_patterns)

    ungrouped: List[Tuple[str, Dict[str, Tuple[List[str], List[str]]]]] = [
        (mp, {}) for mp in ungrouped_mountpoints
    ]
    grouped: List[Tuple[str, Dict[str, Tuple[List[str], List[str]]]]] = [
        (group, {"patterns": group_patterns[group]}) for group in groups
    ]
    return ungrouped + grouped


def df_check_filesystem_single(
    value_store: MutableMapping[str, Any],
    mountpoint: str,
    size_mb: Optional[float],
    avail_mb: Optional[float],
    reserved_mb: Optional[float],
    inodes_total: Optional[float],
    inodes_avail: Optional[float],
    params: Mapping[str, Any],
    this_time=None,
) -> CheckResult:
    if size_mb == 0:
        yield Result(state=State.WARN, summary="Size of filesystem is 0 B")
        return

    if (size_mb is None) or (avail_mb is None) or (reserved_mb is None):
        yield Result(state=State.OK, summary="no filesystem size information")
        return

    # params might still be a tuple
    show_levels, subtract_reserved, show_reserved = (
        params.get("show_levels", False),
        params.get("subtract_reserved", False) and reserved_mb > 0,
        params.get("show_reserved") and reserved_mb > 0,
    )

    used_mb = size_mb - avail_mb
    used_max = size_mb
    if subtract_reserved:
        used_mb -= reserved_mb
        used_max -= reserved_mb

    # Get warning and critical levels already with 'magic factor' applied
    levels = get_filesystem_levels(size_mb / 1024.0, params)
    warn_mb, crit_mb = levels["levels_mb"]

    used_hr = render.bytes(used_mb * 1024**2)
    used_max_hr = render.bytes(used_max * 1024**2)
    used_perc_hr = render.percent(100.0 * used_mb / used_max)

    # If both strings end with the same unit, then drop the first one
    if used_hr.split()[1] == used_max_hr.split()[1]:
        used_hr = used_hr.split()[0]

    if warn_mb < 0.0:
        # Negative levels, so user configured thresholds based on space left. Calculate the
        # upper thresholds based on the size of the filesystem
        crit_mb = used_max + crit_mb
        warn_mb = used_max + warn_mb

    status = State.CRIT if used_mb >= crit_mb else State.WARN if used_mb >= warn_mb else State.OK
    yield Metric("fs_used", used_mb, levels=(warn_mb, crit_mb), boundaries=(0, size_mb))
    yield Metric("fs_size", size_mb, boundaries=(0, None))
    yield Metric(
        "fs_used_percent",
        100.0 * used_mb / size_mb,
        levels=(_mb_to_perc(warn_mb, size_mb), _mb_to_perc(crit_mb, size_mb)),
        boundaries=(0.0, 100.0),
    )

    # Expand infotext according to current params
    infotext = [f"{used_perc_hr} used ({used_hr} of {used_max_hr})"]
    if (
        show_levels == "always"
        or (show_levels == "onproblem" and status is not State.OK)  #
        or (  #
            show_levels == "onmagic" and (status is not State.OK or levels.get("magic", 1.0) != 1.0)
        )
    ):
        infotext.append(levels["levels_text"])
    yield Result(state=status, summary=", ".join(infotext).replace("), (", ", "))

    if show_reserved:
        reserved_perc_hr = render.percent(100.0 * reserved_mb / size_mb)
        reserved_hr = render.bytes(reserved_mb * 1024**2)
        yield Result(
            state=status,
            summary="additionally reserved for root: %s" % reserved_hr  #
            if subtract_reserved
            else f"therein reserved for root: {reserved_perc_hr} ({reserved_hr})",  #
        )

    if subtract_reserved:
        yield Metric("fs_free", avail_mb, boundaries=(0, size_mb))

    if subtract_reserved or show_reserved:
        yield Metric("reserved", reserved_mb)

    yield from size_trend(
        value_store=value_store,
        value_store_key=mountpoint,
        resource="disk",
        levels=levels,
        used_mb=used_mb,
        size_mb=size_mb,
        timestamp=this_time,
    )

    if inodes_total and inodes_avail is not None:
        yield from _check_inodes(levels, inodes_total, inodes_avail)


def df_check_filesystem_list(
    value_store: MutableMapping[str, Any],
    item: str,
    params: Mapping[str, Any],
    fslist_blocks: FSBlocks,
    fslist_inodes=None,
    this_time=None,
) -> CheckResult:
    """Wrapper for `df_check_filesystem_single` supporting groups"""

    def group_sum(metric_name, info, mountpoints_group):
        """Calculate sum of named values for matching mount points"""
        try:
            return sum(
                block_info[metric_name]  #
                for (mp, block_info) in info.items()  #
                if mp in mountpoints_group
            )
        except TypeError:
            return None

    # Translate lists of tuples into convenient dicts
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
        data, inodes_data = blocks_info.get(item, {}), inodes_info.get(item, {})
        yield from df_check_filesystem_single(
            value_store,
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
        yield Result(state=State.UNKNOWN, summary="No filesystem matching the patterns")
        return

    total_size_mb = group_sum("size_mb", blocks_info, matching_mountpoints)
    total_avail_mb = group_sum("avail_mb", blocks_info, matching_mountpoints)
    total_reserved_mb = group_sum("reserved_mb", blocks_info, matching_mountpoints)

    total_inodes = group_sum("inodes_total", inodes_info, matching_mountpoints)
    total_inodes_avail = group_sum("inodes_avail", inodes_info, matching_mountpoints)

    yield from df_check_filesystem_single(
        value_store,
        item,
        total_size_mb,
        total_avail_mb,
        total_reserved_mb,
        total_inodes,
        total_inodes_avail,
        params,
        this_time,
    )

    yield Result(state=State.OK, summary="%d filesystems" % len(matching_mountpoints))


def _mb_to_perc(value: Optional[float], size_mb: float) -> Optional[float]:
    return None if value is None else 100.0 * value / size_mb
