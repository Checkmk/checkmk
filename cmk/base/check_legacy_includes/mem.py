#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections
import time
from numbers import Integral
from typing import Any, List, NamedTuple, Optional

from cmk.base.check_api import get_average, get_bytes_human_readable, get_percent_human_readable
from cmk.base.plugins.agent_based.utils.memory import compute_state, get_levels_mode_from_value
from cmk.base.plugins.agent_based.utils.memory import normalize_levels as normalize_mem_levels

memused_default_levels = (150.0, 200.0)

MEMORY_DEFAULT_LEVELS = {
    "levels": memused_default_levels,
}


class _MemBytesTuple(NamedTuple):
    bytes: int
    kb: float
    mb: float


class MemBytes(_MemBytesTuple):
    def __new__(cls, value):
        return super().__new__(cls, int(value * 1024), float(value), value / 1024.0)

    def render(self):
        return get_bytes_human_readable(self.bytes, base=1024)


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

    infotext = "%s: %s%s - %s of %s%s" % (
        label,
        get_percent_human_readable(100.0 * show_value / total),
        show_text,
        get_bytes_human_readable(show_value, base=1024),
        get_bytes_human_readable(total, base=1024),
        (" %s" % label_total).rstrip(),
    )

    try:
        mode, (warn, crit) = levels
    except (ValueError, TypeError):  # handle None, "ignore"
        mode, (warn, crit) = "ignore", (None, None)

    warn, crit, levels_text = normalize_mem_levels(mode, warn, crit, total)
    state = _compute_state(used, warn, crit)
    if state and levels_text:
        infotext = "%s (%s)" % (infotext, levels_text)

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


def _get_total_usage(ramused, swapused, pagetables):
    """get total usage and a description how it was computed"""
    totalused_kb = ramused.kb
    details = ["RAM"]

    if swapused:
        totalused_kb += swapused.kb
        details.append("Swap")

    if pagetables:
        totalused_kb += pagetables.kb
        details.append("Pagetables")

    totalused = MemBytes(totalused_kb)
    if len(details) == 1:
        return totalused, details[0]
    return totalused, "Total (%s)" % " + ".join(details)


def check_memory(params, meminfo):  # pylint: disable=too-many-branches
    if isinstance(params, tuple):
        params = {"levels": params}

    memtotal = MemBytes(meminfo["MemTotal"])
    memused = MemBytes(memtotal.kb - meminfo["MemFree"])

    swaptotal: Optional[MemBytes]
    swapused: Optional[MemBytes]
    perfdata: List[Any]
    if "SwapFree" in meminfo:
        swaptotal = MemBytes(meminfo["SwapTotal"])
        swapused = MemBytes(swaptotal.kb - meminfo["SwapFree"])
        perfdata = [("swap_used", swapused.bytes, None, None, 0, swaptotal.bytes)]
    else:
        swaptotal = None
        swapused = None
        perfdata = []

    # Size of Pagetable on Linux can be relevant e.g. on ORACLE
    # servers with much memory, that do not use HugeTables. We account
    # that for used
    pagetables: Optional[MemBytes]
    if "PageTables" in meminfo:
        pagetables = MemBytes(meminfo["PageTables"])
        perfdata.append(("mem_lnx_page_tables", pagetables.bytes))
    else:
        pagetables = None

    # Buffers and Cached are optional. On Linux both mean basically the same.
    caches = MemBytes(meminfo.get("Buffers", 0) + meminfo.get("Cached", 0))

    ramused = MemBytes(memused.kb - caches.kb)
    perfdata.append(("mem_used", ramused.bytes, None, None, 0, memtotal.bytes))
    perfdata.append(
        ("mem_used_percent", 100.0 * ramused.bytes / memtotal.bytes, None, None, 0, 100.0)
    )

    totalused, totalused_descr = _get_total_usage(ramused, swapused, pagetables)

    infotext = check_memory_element(
        totalused_descr,
        totalused.bytes,
        memtotal.bytes,
        None,
        label_total="RAM" if totalused_descr != "RAM" else "",
    )[1]

    # Take into account averaging
    average_min = params.get("average")
    if average_min:
        totalused_mb_avg = get_average(
            "mem.used.total", time.time(), totalused.mb, average_min, initialize_zero=False
        )
        totalused_perc_avg = totalused_mb_avg / memtotal.mb * 100
        infotext += ", %d min average %.1f%%" % (average_min, totalused_perc_avg)
        perfdata.append(("memusedavg", totalused_mb_avg))
        comp_mb = totalused_mb_avg
    else:
        comp_mb = totalused.mb

    # Normalize levels and check them
    totalvirt = MemBytes((swaptotal.kb if swaptotal is not None else 0) + memtotal.kb)
    warn, crit = params.get("levels", (None, None))
    mode = get_levels_mode_from_value(warn)
    warn_mb, crit_mb, levels_text = normalize_mem_levels(
        mode,
        abs(warn),
        abs(crit),
        totalvirt.mb,
        _perc_total=memtotal.mb,
        render_unit=1024**2,
    )
    assert isinstance(totalused, MemBytes)
    assert isinstance(warn_mb, Integral)
    assert isinstance(crit_mb, Integral)
    perfdata.append(
        (
            "mem_lnx_total_used",
            totalused.bytes,
            warn_mb * 1024**2,
            crit_mb * 1024**2,
            0,
            totalvirt.bytes,
        )
    )

    # Check levels
    state = _compute_state(comp_mb, warn_mb, crit_mb)
    if state and levels_text:
        infotext = "%s (%s)" % (infotext, levels_text)

    yield state, infotext, perfdata

    # Not sure why the next two lines are necessary: memtotal and ramused
    # are not optional.
    assert isinstance(ramused, MemBytes)
    assert isinstance(memtotal, MemBytes)
    if totalused_descr != "RAM":
        yield check_memory_element(
            "RAM",
            ramused.bytes,  # <- caches subtracted
            memtotal.bytes,
            None,
        )
        assert isinstance(swapused, MemBytes)
        assert isinstance(swaptotal, MemBytes)
        if swaptotal and swaptotal.bytes:
            yield check_memory_element(
                "Swap",
                swapused.bytes,
                swaptotal.bytes,
                None,
            )
        if pagetables:
            yield 0, "Pagetables: %s" % pagetables.render(), []

    # Add additional metrics, provided by Linux.
    if meminfo.get("Mapped"):
        for key, label, metric in (
            ("Mapped", "Mapped", "mem_lnx_mapped"),
            ("Committed_AS", "Committed", "mem_lnx_committed_as"),
            ("Shmem", "Shared", "mem_lnx_shmem"),
        ):
            value = MemBytes(meminfo.get(key, 0))
            yield 0, "%s: %s" % (label, value.render()), [(metric, value.bytes)]
