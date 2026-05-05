#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyResult
from cmk.legacy_includes.mem import check_memory_element

check_info = {}

# FIXME
# The WATO group 'memory_simple' needs an item and the service_description should
# have a '%s'.  At the moment the current empty item '' and 'Memory' without '%s'
# works but is not consistent.  This will be fixed in the future.
# If we change this we loose history and parameter sets have to be adapted.

# .1.3.6.1.4.1.2021.4.2.0 swap      --> UCD-SNMP-MIB::memErrorName.0
# .1.3.6.1.4.1.2021.4.3.0 8388604   --> UCD-SNMP-MIB::MemTotalSwap.0
# .1.3.6.1.4.1.2021.4.4.0 8388604   --> UCD-SNMP-MIB::MemAvailSwap.0
# .1.3.6.1.4.1.2021.4.5.0 4003584   --> UCD-SNMP-MIB::MemTotalReal.0
# .1.3.6.1.4.1.2021.4.11.0 12233816 --> UCD-SNMP-MIB::MemTotalFree.0
# .1.3.6.1.4.1.2021.4.12.0 16000    --> UCD-SNMP-MIB::memMinimumSwap.0
# .1.3.6.1.4.1.2021.4.13.0 3163972  --> UCD-SNMP-MIB::memShared.0
# .1.3.6.1.4.1.2021.4.14.0 30364    --> UCD-SNMP-MIB::memBuffer.0
# .1.3.6.1.4.1.2021.4.15.0 10216780 --> UCD-SNMP-MIB::memCached.0
# .1.3.6.1.4.1.2021.4.100.0 0       --> UCD-SNMP-MIB::memSwapError.0
# .1.3.6.1.4.1.2021.4.101.0         --> UCD-SNMP-MIB::smemSwapErrorMsg.0


def discover_ucd_mem(parsed: Mapping[str, int | str]) -> Iterable[tuple[None, dict[str, Any]]]:
    if parsed:
        yield None, {}


# This function used to be shared with other plugins,
# so it might be over generalized.
def _check_memory_dict(
    meminfo: Mapping[str, Any], params: Mapping[str, Any]
) -> Mapping[
    str,
    tuple[
        int, str, list[tuple[str, float, float | None, float | None, float | None, float | None]]
    ],
]:
    """Check a dictionary of Memory entries against levels.

    Only keys of meminfo that are checked below explicitly are considered.
    All other keys are ignored.
    """
    results = {}  # dict[str, LegacyResult]()

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


def check_ucd_mem(
    _no_item: None, params: dict[str, Any], parsed: Mapping[str, int | str]
) -> Iterable[LegacyResult]:
    if not parsed:
        return

    # general errors
    error = parsed["error"]
    if error and error != "swap":
        yield 1, "Error: %s" % error

    # map legacy levels
    if params.get("levels") is not None:
        params["levels_ram"] = params.pop("levels")

    results = _check_memory_dict(parsed, params)
    yield from results.values()

    # swap errors
    if "error_swap" in parsed:
        if parsed["error_swap"] != 0 and parsed["error_swap_msg"]:
            yield params.get("swap_errors", 0), "Swap error: %s" % parsed["error_swap_msg"]


# This check plug-in uses the migrated section in cmk/base/plugins/agent_based/ucd_mem.py!
# Note: upon migration, move it into that file.
check_info["ucd_mem"] = LegacyCheckDefinition(
    name="ucd_mem",
    service_name="Memory",
    discovery_function=discover_ucd_mem,
    check_function=check_ucd_mem,
    check_ruleset_name="memory_simple_single",
    check_default_parameters={
        "levels": ("perc_used", (80.0, 90.0)),
        "swap_errors": 0,
    },
)
