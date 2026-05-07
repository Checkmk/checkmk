#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.legacy_includes.mem import check_memory_element
from cmk.plugins.lib import memory

check_info = {}


def discover_mem_linux(section):
    if memory.is_linux_section(section):
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


def check_mem_linux(_no_item, params, augmented):
    if not augmented:
        return

    # quick fix: stop modifying parsed data in place!
    augmented = augmented.copy()

    # TODO: Currently some of these values are just set to generate the metrics later
    # See which ones we actually need.

    # SReclaimable is not available for older kernels
    # SwapCached may be missing if swap is disabled, see crash 9d22dcb4-5260-11eb-8458-0b95bfca1bb1
    # Compute memory used by caches, that can be considered "free"
    augmented["Caches"] = (
        augmented["Cached"]
        + augmented["Buffers"]
        + augmented.get("SwapCached", 0)
        + augmented.get("SReclaimable", 0)
    )

    # RAM, https://github.com/Checkmk/checkmk/commit/1657414506bfe8f4001f3e10ef648947276ad75d
    augmented["MemUsed"] = augmented["MemTotal"] - augmented["MemFree"] - augmented["Caches"]
    augmented["SwapUsed"] = augmented["SwapTotal"] - augmented["SwapFree"]
    augmented["TotalTotal"] = augmented["MemTotal"] + augmented["SwapTotal"]
    augmented["TotalUsed"] = augmented["MemUsed"] + augmented["SwapUsed"]

    # Disk Writeback
    augmented["Pending"] = (
        augmented["Dirty"]
        + augmented.get("Writeback", 0)
        + augmented.get("NFS_Unstable", 0)
        + augmented.get("Bounce", 0)
        + augmented.get("WritebackTmp", 0)
    )

    results = {**_check_memory_dict(augmented, params)}

    # show this always:
    yield results.pop("virtual", (0, ""))

    # Note for migration: showing a result only in the details unless it is not ok
    # is exactly what is achieved by usingg `Result(state=..., notice=...)`.
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
    for name, value in sorted(augmented.items()):
        if name.startswith("DirectMap"):
            continue
        if (
            name.startswith("Vmalloc") and augmented["VmallocTotal"] > 2**40
        ):  # useless on 64 Bit system
            continue
        if name.startswith("Huge"):
            if augmented["HugePages_Total"] == 0:  # omit useless data
                continue
            if name == "Hugepagesize":
                continue  # not needed
            value = value * augmented["Hugepagesize"]  # convert number to actual memory size
        metric_name = _camelcase_to_underscored(name.replace("(", "_").replace(")", ""))
        if metric_name not in {
            "mem_used",
            "mem_used_percent",
            "swap_used",
            "committed_as",
            "shmem",
            "page_tables",
        }:
            yield 0, "", [(metric_name, value)]


# ThisIsACamel -> this_is_a_camel
def _camelcase_to_underscored(name: str) -> str:
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
    name="mem_linux",
    service_name="Memory",
    sections=["mem"],
    discovery_function=discover_mem_linux,
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
