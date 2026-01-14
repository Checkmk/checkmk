#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="arg-type"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.mem import check_memory_dict
from cmk.plugins.lib import memory

check_info = {}


def discover_mem_linux(section):
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

    # RAM, https://github.com/Checkmk/checkmk/commit/1657414506bfe8f4001f3e10ef648947276ad75d
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

    results = {**check_memory_dict(section, params)}

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
        metric_name = _camelcase_to_underscored(name.replace("(", "_").replace(")", ""))
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
def _camelcase_to_underscored(name):
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
