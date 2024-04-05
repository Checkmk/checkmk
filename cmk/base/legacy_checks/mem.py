#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

import time
from collections.abc import Mapping
from typing import Generator, Literal, NotRequired, TypedDict

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.mem import check_memory_dict, check_memory_element
from cmk.base.config import check_info

from cmk.agent_based.v2 import get_average, get_value_store, render
from cmk.plugins.lib import memory

#   .--mem.linux-----------------------------------------------------------.
#   |                                      _ _                             |
#   |           _ __ ___   ___ _ __ ___   | (_)_ __  _   ___  __           |
#   |          | '_ ` _ \ / _ \ '_ ` _ \  | | | '_ \| | | \ \/ /           |
#   |          | | | | | |  __/ | | | | |_| | | | | | |_| |>  <            |
#   |          |_| |_| |_|\___|_| |_| |_(_)_|_|_| |_|\__,_/_/\_\           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Specialized memory check for Linux that takes into account          |
#   |  all of its specific information in /proc/meminfo.                   |
#   '----------------------------------------------------------------------'


def inventory_mem_linux(section):
    if memory.is_linux_section(section):
        yield None, {}


def check_mem_linux(_no_item, params, section):
    if not section:
        return

    # quick fix: stop modifying parsed data in place!
    section = section.copy()

    # TODO: Currently some of these values are just set to generate the metrics later
    # See which ones we actually need.

    # SReclaimable is not available for older kernels
    # SwapCached may be missing if swap is disabled, see crash 9d22dcb4-5260-11eb-8458-0b95bfca1bb1
    # Compute memory used by caches, that can be considered "free"
    section["Caches"] = (
        section["Cached"]
        + section["Buffers"]
        + section.get("SwapCached", 0)
        + section.get("SReclaimable", 0)
    )

    section["MemUsed"] = section["MemTotal"] - section["MemFree"] - section["Caches"]
    section["SwapUsed"] = section["SwapTotal"] - section["SwapFree"]
    section["TotalTotal"] = section["MemTotal"] + section["SwapTotal"]
    section["TotalUsed"] = section["MemUsed"] + section["SwapUsed"]

    # Disk Writeback
    section["Pending"] = (
        section["Dirty"]
        + section.get("Writeback", 0)
        + section.get("NFS_Unstable", 0)
        + section.get("Bounce", 0)
        + section.get("WritebackTmp", 0)
    )

    results = check_memory_dict(section, params)

    # show this always:
    yield results.pop("virtual", (0, ""))

    details_results = []
    for state, text, metrics in results.values():
        if state:
            yield state, text, metrics
        else:
            details_results.append((state, text, metrics))
    MARK_AS_DETAILS = "\n"
    for state, text, perf in details_results:
        yield state, f"{MARK_AS_DETAILS}{text}", perf

    # Now send performance data. We simply output *all* fields of section
    # except for a few really useless values
    perfdata = []
    for name, value in sorted(section.items()):
        if name.startswith("DirectMap"):
            continue
        if (
            name.startswith("Vmalloc") and section["VmallocTotal"] > 2**40
        ):  # useless on 64 Bit system
            continue
        if name.startswith("Huge"):
            if section["HugePages_Total"] == 0:  # omit useless data
                continue
            if name == "Hugepagesize":
                continue  # not needed
            value = value * section["Hugepagesize"]  # convert number to actual memory size
        metric_name = camelcase_to_underscored(name.replace("(", "_").replace(")", ""))
        if metric_name not in {
            "mem_used",
            "mem_used_percent",
            "swap_used",
            "committed_as",
            "shmem",
            "page_tables",
        }:
            perfdata.append((metric_name, value))
    yield 0, "", perfdata


# ThisIsACamel -> this_is_a_camel
def camelcase_to_underscored(name):
    previous_lower = False
    previous_underscore = True
    result = ""
    for char in name:
        if char.isupper():
            if previous_lower and not previous_underscore:
                result += "_"
            previous_lower = False
            previous_underscore = False
            result += char.lower()
        elif char == "_":
            previous_lower = False
            previous_underscore = True
            result += char
        else:
            previous_lower = True
            previous_underscore = False
            result += char
    return result


check_info["mem.linux"] = LegacyCheckDefinition(
    service_name="Memory",
    sections=["mem"],
    discovery_function=inventory_mem_linux,
    check_function=check_mem_linux,
    check_ruleset_name="memory_linux",
    check_default_parameters={
        "levels_virtual": ("perc_used", (80.0, 90.0)),
        "levels_total": ("perc_used", (120.0, 150.0)),
        "levels_shm": ("perc_used", (20.0, 30.0)),
        "levels_pagetables": ("perc_used", (8.0, 16.0)),
        "levels_committed": ("perc_used", (100.0, 150.0)),
        "levels_commitlimit": ("perc_free", (20.0, 10.0)),
        "levels_vmalloc": ("abs_free", (50 * 1024 * 1024, 30 * 1024 * 1024)),
        "levels_hardwarecorrupted": ("abs_used", (1, 1)),
    },
)

# .
#   .--mem.used------------------------------------------------------------.
#   |                                                        _             |
#   |           _ __ ___   ___ _ __ ___   _   _ ___  ___  __| |            |
#   |          | '_ ` _ \ / _ \ '_ ` _ \ | | | / __|/ _ \/ _` |            |
#   |          | | | | | |  __/ | | | | || |_| \__ \  __/ (_| |            |
#   |          |_| |_| |_|\___|_| |_| |_(_)__,_|___/\___|\__,_|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Memory check that takes into account the swap space. This check is   |
#   | used for unixoide operating systems.                                 |
#   '----------------------------------------------------------------------'


# .
#   .--mem.win-------------------------------------------------------------.
#   |                                                _                     |
#   |              _ __ ___   ___ _ __ ___ __      _(_)_ __                |
#   |             | '_ ` _ \ / _ \ '_ ` _ \\ \ /\ / / | '_ \               |
#   |             | | | | | |  __/ | | | | |\ V  V /| | | | |              |
#   |             |_| |_| |_|\___|_| |_| |_(_)_/\_/ |_|_| |_|              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Windows now has a dedicated memory check that reflect the special    |
#   | nature of the page file.                                             |
#   '----------------------------------------------------------------------'

_MB = 1024**2

# Special memory and page file check for Windows


def inventory_mem_win(section):
    if "MemTotal" in section and "PageTotal" in section:
        yield None, {}


_PercUsed = tuple[float, float]
_AbsFree = tuple[int, int]
_Predictive = Mapping[str, object]
# Note: `None` is implemented, und should be possible. It can't occur due to poor ruleset design currenty.
_Levels = _PercUsed | _AbsFree | _Predictive | None
_LevelsType = Literal["perc_used", "abs_free", "predictive"]


class _Params(TypedDict):
    average: NotRequired[int]
    memory: _Levels
    pagefile: _Levels


def _parse_levels(
    levels: _Levels,
) -> (
    tuple[Literal["perc_used"], _PercUsed]
    | tuple[Literal["abs_free"], _AbsFree]
    | tuple[Literal["predictive"], _Predictive]
    | None
):
    if levels is None:
        return None
    if not isinstance(levels, tuple):
        return "predictive", levels
    if isinstance(levels[0], float):
        return "perc_used", (float(levels[0]), float(levels[1]))
    return "abs_free", (int(levels[0]), int(levels[1]))


def _get_levels_type_and_value(
    levels_value: _Levels,
) -> (
    tuple[Literal["perc_used"], _PercUsed]
    | tuple[Literal["abs_free"], _AbsFree]
    | tuple[Literal["predictive"], _Predictive]
    | tuple[Literal["ignore"], tuple[None, None]]
):
    if (parsed_levels := _parse_levels(levels_value)) is None:
        return "ignore", (None, None)

    return (
        parsed_levels
        if parsed_levels[0] != "abs_free"
        else (
            "abs_free",
            (
                # absolute levels on free space come in MB, which cannot be changed easily
                parsed_levels[1][0] * _MB,
                parsed_levels[1][1] * _MB,
            ),
        )
    )


def _do_averaging(
    timestamp: float,
    average_horizon_min: float,
    paramname: Literal["memory", "pagefile"],
    used: float,
    total: float,
) -> tuple[float, str]:
    used_avg = (
        get_average(
            get_value_store(),
            "mem.win.%s" % paramname,
            timestamp,
            used / 1024.0,  # use kB for compatibility
            average_horizon_min,
        )
        * 1024
    )
    return (
        used_avg,
        "%d min average: %s (%s)"
        % (
            average_horizon_min,
            render.percent(100.0 * used_avg / total),
            render.bytes(used_avg),
        ),
    )


def check_mem_windows(
    _no_item: None, params: _Params, section: memory.SectionMem
) -> Generator[tuple[int, str, list], None, None]:
    now = time.time()

    for title, prefix, paramname, metric_name, levels in (
        ("RAM", "Mem", "memory", "mem_used", params["memory"]),
        ("Commit charge", "Page", "pagefile", "pagefile_used", params["pagefile"]),
    ):
        try:
            total = section["%sTotal" % prefix]
            free = section["%sFree" % prefix]
        except KeyError:
            continue
        # Metrics for total mem and pagefile are expected in MB
        yield 0, "", [(metric_name.replace("used", "total"), total / _MB)]

        used = float(total - free)

        parsed_levels = _get_levels_type_and_value(levels)
        average = params.get("average")

        state, infotext, perfdata = check_memory_element(
            title,
            used,
            total,
            None if average is not None or parsed_levels[0] == "predictive" else parsed_levels,
            metric_name=metric_name,
            create_percent_metric=title == "RAM",
        )

        # Do averaging, if configured, just for matching the levels
        if average is not None:
            used, infoadd = _do_averaging(
                now,
                average,
                paramname,
                used,
                total,
            )
            infotext += f", {infoadd}"

            if parsed_levels[0] != "predictive":
                state, _infotext, perfadd = check_memory_element(
                    title,
                    used,
                    total,
                    parsed_levels,
                    metric_name=paramname + "_avg",
                )

                perfdata.append(
                    (
                        (averaged_metric := perfadd[0])[0],
                        # the averaged metrics are expected to be in MB
                        *(v / _MB if v is not None else None for v in averaged_metric[1:]),
                    )
                )

        if parsed_levels[0] == "predictive":
            state, infoadd, perfadd = check_levels(
                used / _MB,  # Current value stored in MB in RRDs
                ("%s_avg" % paramname) if average else paramname,
                parsed_levels[1],
                unit="GiB",  # Levels are specified in GiB...
                scale=1024,  # ... in WATO ValueSpec
                infoname=title,
            )
            if infoadd:
                infotext += ", " + infoadd
            perfdata += perfadd

        yield state, infotext, perfdata


check_info["mem.win"] = LegacyCheckDefinition(
    service_name="Memory",
    sections=["mem"],
    discovery_function=inventory_mem_win,
    check_function=check_mem_windows,
    check_ruleset_name="memory_pagefile_win",
    check_default_parameters=_Params(
        memory=(80.0, 90.0),
        pagefile=(80.0, 90.0),
    ),
)

# .
#   .--mem.vmalloc---------------------------------------------------------.
#   |                                                   _ _                |
#   |    _ __ ___   ___ _ __ ___ __   ___ __ ___   __ _| | | ___   ___     |
#   |   | '_ ` _ \ / _ \ '_ ` _ \\ \ / / '_ ` _ \ / _` | | |/ _ \ / __|    |
#   |   | | | | | |  __/ | | | | |\ V /| | | | | | (_| | | | (_) | (__     |
#   |   |_| |_| |_|\___|_| |_| |_(_)_/ |_| |_| |_|\__,_|_|_|\___/ \___|    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | This very specific check checks the usage and fragmentation of the   |
#   | address space 'vmalloc' that can be problematic on 32-Bit systems.   |
#   | It is superseeded by the new check mem.linux and will be removed     |
#   | soon.                                                                |
#   '----------------------------------------------------------------------'


def inventory_mem_vmalloc(section):
    if memory.is_linux_section(section):
        return  # handled by new Linux memory check

    # newer kernel version report wrong data,
    # i.d. both VmallocUsed and Chunk equal zero
    if "VmallocTotal" in section and not (
        section["VmallocUsed"] == 0 and section["VmallocChunk"] == 0
    ):
        # Do not checks this on 64 Bit systems. They have almost
        # infinitive vmalloc
        if section["VmallocTotal"] < 4 * 1024**2:
            yield None, {}


def check_mem_vmalloc(_item, params, section):
    total_mb = section["VmallocTotal"] / 1024.0**2
    used_mb = section["VmallocUsed"] / 1024.0**2
    chunk_mb = section["VmallocChunk"] / 1024.0**2
    used_warn_perc, used_crit_perc = params["levels_used_perc"]

    yield 0, f"Total: {total_mb:.1f} MB"
    yield check_levels(
        used_mb,
        dsname="used",
        params=(total_mb * used_warn_perc / 100, total_mb * used_crit_perc / 100),
        human_readable_func=lambda v: f"{v:.1f}",
        unit="MB",
        infoname="Used",
        boundaries=(0, total_mb),
    )
    yield check_levels(
        chunk_mb,
        dsname="chunk",
        params=(None, None) + params["levels_lower_chunk_mb"],
        human_readable_func=lambda v: f"{v:.1f}",
        unit="MB",
        infoname="Largest chunk",
        boundaries=(0, total_mb),
    )


check_info["mem.vmalloc"] = LegacyCheckDefinition(
    service_name="Vmalloc address space",
    sections=["mem"],
    discovery_function=inventory_mem_vmalloc,
    check_function=check_mem_vmalloc,
    check_default_parameters={
        "levels_used_perc": (80.0, 90.0),
        "levels_lower_chunk_mb": (64, 32),
    },
)
