#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections

from cmk.agent_based.v2 import render
from cmk.plugins.lib.memory import compute_state
from cmk.plugins.lib.memory import normalize_levels as normalize_mem_levels

memused_default_levels = (150.0, 200.0)

MEMORY_DEFAULT_LEVELS = {
    "levels": memused_default_levels,
}


def _compute_state(value, warn, crit):
    return int(compute_state(value, warn, crit))


#############################################################################
#    This function is already migrated and available in utils/memory.py !   #
#############################################################################
def check_memory_element(
    label,
    used,
    total,
    levels,
    label_total="",
    show_free=False,
    metric_name=None,
    create_percent_metric=False,
):
    """Return a check result for one memory element"""
    if show_free:
        show_value = total - used
        show_text = " free"
    else:
        show_value = used
        show_text = ""

    infotext = "{}: {}{} - {} of {}{}".format(
        label,
        render.percent(100.0 * show_value / total),
        show_text,
        render.bytes(show_value),
        render.bytes(total),
        (" %s" % label_total).rstrip(),
    )

    try:
        mode, (warn, crit) = levels
    except (ValueError, TypeError):  # handle None, "ignore"
        mode, (warn, crit) = "ignore", (None, None)

    warn, crit, levels_text = normalize_mem_levels(mode, warn, crit, total)
    state = _compute_state(used, warn, crit)
    if state and levels_text:
        infotext = f"{infotext} ({levels_text})"

    perf = []
    if metric_name:
        perf.append((metric_name, used, warn, crit, 0, total))
    if create_percent_metric:
        scale_to_perc = 100.0 / total
        perf.append(
            (
                "mem_used_percent",
                used * scale_to_perc,
                warn * scale_to_perc if warn is not None else None,
                crit * scale_to_perc if crit is not None else None,
                0,
                None,  # some times over 100%!
            )
        )

    return state, infotext, perf


def check_memory_dict(meminfo, params):
    """Check a dictionary of Memory entries against levels.

    Only keys of meminfo that are checked below explicitly are considered.
    All other keys are ignored.
    """
    results = collections.OrderedDict()

    # RAM
    if "MemUsed" in meminfo and "MemTotal" in meminfo:
        results["ram"] = check_memory_element(
            "RAM",
            meminfo["MemUsed"],
            meminfo["MemTotal"],
            params.get("levels_ram"),
            metric_name="mem_used",
            create_percent_metric=True,
        )

    # Swap
    if "SwapUsed" in meminfo and meminfo.get("SwapTotal"):
        results["swap"] = check_memory_element(
            "Swap",
            meminfo["SwapUsed"],
            meminfo["SwapTotal"],
            params.get("levels_swap"),
            metric_name="swap_used",
        )
    # Total virtual memory
    if all(k in meminfo for k in ("MemTotal", "MemUsed", "SwapTotal", "SwapUsed")):
        virtual_used = meminfo["MemUsed"] + meminfo["SwapUsed"]
        virtual_total = meminfo["MemTotal"] + meminfo["SwapTotal"]
        results["virtual"] = check_memory_element(
            "Total virtual memory",
            virtual_used,
            virtual_total,
            params.get("levels_virtual"),
        )

        # Committed memory, only if we have virtual_total
        if "Committed_AS" in meminfo:
            results["committed"] = check_memory_element(
                "Committed",
                meminfo["Committed_AS"],
                virtual_total,
                params.get("levels_committed"),
                label_total="virtual memory",
                metric_name="mem_lnx_committed_as",
            )

        # Commit limit
        if "CommitLimit" in meminfo:
            results["commitlimit"] = check_memory_element(
                "Commit Limit",
                virtual_total - meminfo["CommitLimit"],
                virtual_total,
                params.get("levels_commitlimit"),
                label_total="virtual memory",
            )

    # Shared memory
    if "Shmem" in meminfo and "MemTotal" in meminfo:
        results["shm"] = check_memory_element(
            "Shared memory",
            meminfo["Shmem"],
            meminfo["MemTotal"],
            params.get("levels_shm"),
            label_total="RAM",
            metric_name="mem_lnx_shmem",
        )

    # Page tables
    if "PageTables" in meminfo and "MemTotal" in meminfo:
        results["pagetables"] = check_memory_element(
            "Page tables",
            meminfo["PageTables"],
            meminfo["MemTotal"],
            params.get("levels_pagetables"),
            label_total="RAM",
            metric_name="mem_lnx_page_tables",
        )

    # Disk Writeback
    if "Pending" in meminfo and "MemTotal" in meminfo:
        results["pending"] = check_memory_element(
            "Disk Writeback",
            meminfo["Pending"],
            meminfo["MemTotal"],
            params.get("levels_writeback"),
            label_total="RAM",
        )

    # Available Memory
    if "MemAvailable" in meminfo and "MemTotal" in meminfo:
        results["available"] = check_memory_element(
            "RAM available",
            meminfo["MemTotal"] - meminfo["MemAvailable"],
            meminfo["MemTotal"],
            params.get("levels_available"),
            show_free=True,
        )

    # VMalloc,
    # newer kernel version report wrong data,
    # i.d. VMalloc Chunk equal zero
    if "VmallocUsed" in meminfo and "VmallocChunk" in meminfo and meminfo["VmallocChunk"]:
        results["vmalloc"] = check_memory_element(
            "Largest Free VMalloc Chunk",
            meminfo["VmallocTotal"] - meminfo["VmallocChunk"],
            meminfo["VmallocTotal"],
            params.get("levels_vmalloc"),
            label_total="VMalloc Area",
            show_free=True,
        )

    # HardwareCorrupted
    if "HardwareCorrupted" in meminfo and "MemTotal" in meminfo:
        results["corrupted"] = check_memory_element(
            "Hardware Corrupted",
            meminfo["HardwareCorrupted"],
            meminfo["MemTotal"],
            params.get("levels_hardwarecorrupted"),
            label_total="RAM",
        )

    return results
