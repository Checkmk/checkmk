#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fnmatch
from collections.abc import Callable, Generator, Iterable, Mapping, MutableMapping, Sequence
from enum import Enum
from typing import Any, Literal, NamedTuple, NewType

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Metric, render, Result, Service, State

from .size_trend import size_trend


class DfBlock(NamedTuple):
    device: str
    fs_type: str | None
    size_mb: float
    avail_mb: float
    reserved_mb: float
    mountpoint: str
    uuid: str | None


class DfInode(NamedTuple):
    device: str | None
    total: int
    avail: int
    mountpoint: str
    uuid: str | None


FSBlock = tuple[str, float | None, float | None, float]
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

# Filesystems to ignore.
# They should not be sent by agent anyway and will indeed not be sent on Linux beginning with 1.6.0
EXCLUDED_MOUNTPOINTS = ("/dev", "")

FILESYSTEM_DEFAULT_LEVELS: Mapping[str, Any] = {
    "levels": (80.0, 90.0),  # warn/crit in percent
}

TREND_DEFAULT_PARAMS: Mapping[str, Any] = {
    "trend_range": 24,
    "trend_perfdata": True,  # do send performance data for trends
}

MAGIC_FACTOR_DEFAULT_PARAMS: Mapping[str, Any] = {
    "magic_normsize": 20,  # Standard size if 20 GB
    "levels_low": (50.0, 60.0),  # Never move warn level below 50% due to magic factor
}


SHOW_LEVELS_DEFAULT: Mapping[str, Any] = {
    "show_levels": "onmagic",
}

INODES_DEFAULT_PARAMS: Mapping[str, Any] = {
    "inodes_levels": (10.0, 5.0),
    "show_inodes": "onlow",
}


FILESYSTEM_DEFAULT_PARAMS: Mapping[str, Any] = {
    **FILESYSTEM_DEFAULT_LEVELS,
    **MAGIC_FACTOR_DEFAULT_PARAMS,
    **SHOW_LEVELS_DEFAULT,
    **INODES_DEFAULT_PARAMS,
    "show_reserved": False,
    **TREND_DEFAULT_PARAMS,
}


def _determine_levels_for_filesystem(levels: list, filesystem_size: Bytes) -> tuple[Any, Any]:
    """Determine levels based on the given filesystem size from a list of
    levels configured by the user.

    The list consists of a tuple of filesystem size (GB) and another tuple of
    levels (warn/crit). The levels are only selected for the filesystem if it
    is greater than the filesystem size in the list. If levels cannot be
    determined, a default of 100% for warn and crit is used.

    Examples:

    >>> _determine_levels_for_filesystem([(20, (1, 2)), (30, (3, 4)), (50, (5, 6))], 20)
    (100.0, 100.0)

    >>> _determine_levels_for_filesystem([(20, (1, 2)), (30, (3, 4)), (50, (5, 6))], 30)
    (1, 2)

    >>> _determine_levels_for_filesystem([(20, (1, 2)), (30, (3, 4)), (50, (5, 6))], 40)
    (3, 4)

    >>> _determine_levels_for_filesystem([(20, (1, 2)), (30, (3, 4)), (50, (5, 6))], 100)
    (5, 6)
    """

    for size, actual_levels in sorted(levels, reverse=True):
        if filesystem_size > size:
            return actual_levels

    # TODO: if the levels are not found, the defaults should be used
    return 100.0, 100.0


def _adjust_level(level: Percent, factor: float) -> Percent:
    return Percent(100 - ((100 - level) * factor))


def _adjust_levels(
    levels: FilesystemLevels,
    factor: float,
    filesystem_size: Bytes,
    reference_size: Bytes,
    minimum_levels: tuple[float, float],
) -> FilesystemLevels:
    """The magic factor adjusts thresholds set for free or used filesystem
    space based on a factor (aka "magic factor") and relative to a
    reference size (aka "magic normsize").

    The reasoning is that it does not make sense to apply the same
    thresholds to all filesystems, regardless of their size. For example,
    20% of space on a 50TB filesytem could be considered sufficiently free
    space, while 20% on a 1GB filesystem could indicate that it needs to be
    expanded/freed.

    The reference size is the size at which we "start adjusting". The
    thresholds for filesystems larger than the reference size become more
    lenient (i.e. higher), while the thresholds for filesystems smaller
    than the reference size become more strict (i.e. lower).

    The magic factor should be a number between 0 and 1, and is the
    magnitude of adjustment. The closer this number is to 1, the smaller is
    this magnitude. A factor of 1 does not adjust the thresholds.

    Example:

    reference size: 20GB
    threshold: 80%

    Filesystem size    MF 1    MF 0.9    MF 0.5
    10GB               80%     79%       72%
    20GB               80%     80%       80%
    50GB               80%     82%       87%


    Please run df_magic_factor.py for more examples.
    """

    relative_size = filesystem_size / reference_size
    true_factor = (relative_size**factor) / relative_size

    warn_percent = (
        Percent(max(_adjust_level(levels.warn_percent, true_factor), minimum_levels[0]))
        if factor != 1.0
        else levels.warn_percent
    )
    crit_percent = (
        Percent(max(_adjust_level(levels.crit_percent, true_factor), minimum_levels[1]))
        if factor != 1.0
        else levels.crit_percent
    )

    if isinstance(levels, LevelsFreeSpace):
        return LevelsFreeSpace(
            warn_percent=warn_percent,
            crit_percent=crit_percent,
            warn_absolute=_to_absolute(warn_percent, filesystem_size),
            crit_absolute=_to_absolute(crit_percent, filesystem_size),
            render_as=levels.render_as,
        )

    return LevelsUsedSpace(
        warn_percent=warn_percent,
        crit_percent=crit_percent,
        warn_absolute=_to_absolute(warn_percent, filesystem_size),
        crit_absolute=_to_absolute(crit_percent, filesystem_size),
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


def _ungrouped_mountpoints_and_groups(
    mount_points: Iterable[str],
    group_patterns: Mapping[str, tuple[Sequence[str], Sequence[str]]],
) -> tuple[set[str], Mapping[str, set[str]]]:
    ungrouped_mountpoints = set(mount_points)
    groups: dict[str, set[str]] = {}
    for group_name, (patterns_include, patterns_exclude) in group_patterns.items():
        mp_groups = mountpoints_in_group(mount_points, patterns_include, patterns_exclude)
        if mp_groups:
            groups[group_name] = set(mp_groups)
            ungrouped_mountpoints = ungrouped_mountpoints.difference(mp_groups)
    return ungrouped_mountpoints, groups


def get_filesystem_levels(
    filesystem_size_gb: float,
    params: Mapping[str, Any],
) -> FilesystemLevels:
    filesystem_size = Bytes(int(filesystem_size_gb * 1024 * 1024 * 1024))

    filesystem_levels = _parse_filesystem_levels(params["levels"], filesystem_size)

    if (magic_factor := params.get("magic")) is not None:
        filesystem_levels = _adjust_levels(
            filesystem_levels,
            factor=magic_factor,
            filesystem_size=filesystem_size,
            reference_size=Bytes(params["magic_normsize"] * 1024 * 1024 * 1024),
            minimum_levels=params["levels_low"],
        )

    return filesystem_levels


def mountpoints_in_group(
    mplist: Iterable[str],
    patterns_include: Sequence[str],
    patterns_exclude: Sequence[str],
) -> list[str]:
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


def check_inodes(
    levels: Mapping[str, Any],
    inodes_total: float,
    inodes_avail: float,
) -> Generator[Metric | Result, None, None]:
    """
    >>> levels = {
    ...     "inodes_levels": (10, 5),
    ...     "show_inodes": "onproblem",
    ... }
    >>> for r in check_inodes(levels, 80, 60): print(r)
    Metric('inodes_used', 20.0, levels=(70.0, 75.0), boundaries=(0.0, 80.0))
    Result(state=<State.OK: 0>, notice='Inodes used: 20, Inodes available: 60 (75.00%)')

    >>> levels["show_inodes"] = "always"
    >>> for r in check_inodes(levels, 80, 20): print(r)
    Metric('inodes_used', 60.0, levels=(70.0, 75.0), boundaries=(0.0, 80.0))
    Result(state=<State.OK: 0>, summary='Inodes used: 60, Inodes available: 20 (25.00%)')

    >>> levels["show_inodes"]="onlow"
    >>> levels["inodes_levels"]= (40, 35)
    >>> for r in check_inodes(levels, 80, 20): print(r)
    Metric('inodes_used', 60.0, levels=(40.0, 45.0), boundaries=(0.0, 80.0))
    Result(state=<State.CRIT: 2>, summary='Inodes used: 60 (warn/crit at 40/45), Inodes available: 20 (25.00%)')

    >>> levels["inodes_levels"] = None
    >>> for r in check_inodes(levels, 80, 20): print(r)
    Metric('inodes_used', 60.0, boundaries=(0.0, 80.0))
    Result(state=<State.OK: 0>, summary='Inodes used: 60, Inodes available: 20 (25.00%)')
    """
    levels_upper, render_func = _inodes_levels_and_render_func(
        inodes_total,
        levels.get("inodes_levels"),
    )

    inode_result, inode_metric = check_levels_v1(
        value=inodes_total - inodes_avail,
        levels_upper=levels_upper,
        metric_name="inodes_used",
        render_func=render_func,
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


def _inodes_levels_and_render_func(
    inodes_total: float,
    configured_leves: tuple[float, float] | tuple[int, int] | None,
) -> tuple[tuple[float, float] | None, Callable[[float], str]]:
    if configured_leves is None:
        return None, _render_integer

    inodes_warn_variant, inodes_crit_variant = configured_leves

    if isinstance(inodes_warn_variant, int) and isinstance(inodes_crit_variant, int):
        # Levels in absolute numbers
        return (
            (
                inodes_total - inodes_warn_variant,
                inodes_total - inodes_crit_variant,
            ),
            _render_integer,
        )

    if isinstance(inodes_warn_variant, float) and isinstance(inodes_crit_variant, float):
        # Levels in percent
        return (
            (
                (100 - inodes_warn_variant) / 100.0 * inodes_total,
                (100 - inodes_crit_variant) / 100.0 * inodes_total,
            ),
            lambda inodes: render.percent(100.0 * inodes / inodes_total),
        )

    raise TypeError(
        f"Expected tuple of int or tuple of float for inodes levels, got {type(inodes_warn_variant).__name__}/{type(inodes_crit_variant).__name__}"
    )


_GroupingSpec = tuple[list[str], list[str]]


def df_discovery(
    params: Iterable[Mapping[str, Any]],
    mplist: Iterable[str],
) -> DiscoveryResult:
    group_patterns: dict[str, _GroupingSpec] = {}
    for groups in params:
        for group in groups.get("groups", []):
            grouping_entry = group_patterns.setdefault(group["group_name"], ([], []))
            grouping_entry[0].extend(group["patterns_include"])
            grouping_entry[1].extend(group["patterns_exclude"])

    ungrouped_mountpoints, groups = _ungrouped_mountpoints_and_groups(mplist, group_patterns)

    yield from (Service(item=mp) for mp in ungrouped_mountpoints)
    yield from (
        Service(
            item=group,
            parameters={"patterns": group_patterns[group]},
        )
        for group in groups
    )


def check_filesystem_levels(
    filesystem_size: float,
    allocatable_filesystem_size: float,
    free_space: float,
    used_space: float,
    params: Mapping[str, Any],
    show_levels: Literal["onmagic", "always", "onproblem"] = "onproblem",
) -> Generator[Result | Metric, None, None]:
    # Get warning and critical levels already with 'magic factor' applied
    filesystem_levels = get_filesystem_levels(filesystem_size / 1024.0, params)
    warn_mb, crit_mb = (
        filesystem_levels.warn_absolute / 1024**2,
        filesystem_levels.crit_absolute / 1024**2,
    )

    if warn_mb < 0.0:
        # Negative levels, so user configured thresholds based on space left. Calculate the
        # upper thresholds based on the size of the filesystem
        crit_mb = allocatable_filesystem_size + crit_mb
        warn_mb = allocatable_filesystem_size + warn_mb

    status = (
        State.CRIT if used_space >= crit_mb else State.WARN if used_space >= warn_mb else State.OK
    )
    yield Metric("fs_used", used_space, levels=(warn_mb, crit_mb), boundaries=(0, filesystem_size))
    yield Metric("fs_free", free_space, boundaries=(0, None))

    used_space_percent = (used_space / allocatable_filesystem_size) * 100.0
    yield Metric(
        "fs_used_percent",
        used_space_percent,
        levels=(
            _mb_to_perc(warn_mb, allocatable_filesystem_size),
            _mb_to_perc(crit_mb, allocatable_filesystem_size),
        ),
        boundaries=(0.0, 100.0),
    )

    # Expand infotext according to current params
    summary = (
        f"Used: {render.percent(used_space_percent)} "
        f"- {render.bytes(used_space * 1024**2)} of {render.bytes(allocatable_filesystem_size * 1024**2)}"
    )
    if (
        show_levels == "always"
        or (show_levels == "onproblem" and status is not State.OK)  #
        or (  #
            show_levels == "onmagic" and (status is not State.OK or params.get("magic", 1.0) != 1.0)
        )
    ):
        summary = f"{summary} {_check_summary_text(filesystem_levels)}"
    yield Result(state=status, summary=summary)


def df_check_filesystem_single(
    value_store: MutableMapping[str, Any],
    mountpoint: str,
    filesystem_size: float | None,
    free_space: float | None,
    reserved_space: float | None,
    inodes_total: float | None,
    inodes_avail: float | None,
    params: Mapping[str, Any],
    this_time: float | None = None,
) -> CheckResult:
    if filesystem_size == 0:
        yield Result(state=State.WARN, summary="Size of filesystem is 0 B")
        return

    if (filesystem_size is None) or (free_space is None) or (reserved_space is None):
        yield Result(state=State.OK, summary="no filesystem size information")
        return

    # params might still be a tuple
    show_levels, subtract_reserved, show_reserved = (
        params.get("show_levels", "onproblem"),
        params.get("subtract_reserved", False) and reserved_space > 0,
        params.get("show_reserved") and reserved_space > 0,
    )

    if subtract_reserved:
        allocatable_filesystem_size = filesystem_size - reserved_space
    else:
        allocatable_filesystem_size = filesystem_size

    used_space = allocatable_filesystem_size - free_space

    yield from check_filesystem_levels(
        filesystem_size, allocatable_filesystem_size, free_space, used_space, params, show_levels
    )

    # This is used to draw some pretty perfometers
    yield Metric("fs_size", filesystem_size, boundaries=(0, None))

    if show_reserved:
        reserved_perc_hr = render.percent(100.0 * reserved_space / filesystem_size)
        reserved_hr = render.bytes(reserved_space * 1024**2)
        yield Result(
            state=State.OK,
            summary=(
                "additionally reserved for root: %s" % reserved_hr  #
                if subtract_reserved
                else f"therein reserved for root: {reserved_perc_hr} ({reserved_hr})"
            ),  #
        )

    if subtract_reserved:
        yield Metric("reserved", reserved_space)

    yield from size_trend(
        value_store=value_store,
        value_store_key=mountpoint,
        resource="disk",
        levels=params,
        used_mb=used_space,
        size_mb=filesystem_size,
        timestamp=this_time,
    )

    if inodes_total and inodes_avail is not None:
        yield from check_inodes(params, inodes_total, inodes_avail)


def df_check_filesystem_list(
    value_store: MutableMapping[str, Any],
    item: str,
    params: Mapping[str, Any],
    fslist_blocks: FSBlocks,
    fslist_inodes: Sequence[tuple[str, float | None, float | None]] = (),
    this_time: float | None = None,
) -> CheckResult:
    """Wrapper for `df_check_filesystem_single` supporting groups"""

    def group_sum(
        metric_name: str, info: dict[str, dict[str, float | None]], mountpoints_group: list[str]
    ) -> float | None:
        """Calculate sum of named values for matching mount points"""
        try:
            # If we have a None, sum will throw a TypeError which we catch...
            return sum(
                block_info[metric_name]  # type: ignore[misc]
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
        for mountp, size_mb, avail_mb, reserved_mb in fslist_blocks
    }
    inodes_info = {
        mountp: {
            "inodes_total": inodes_total,
            "inodes_avail": inodes_avail,
        }
        for mountp, inodes_total, inodes_avail in fslist_inodes
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


def _mb_to_perc(value: float | None, size_mb: float) -> float | None:
    return None if value is None else 100.0 * value / size_mb
