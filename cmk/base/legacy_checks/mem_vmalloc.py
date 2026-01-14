#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="arg-type"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.plugins.lib import memory

check_info = {}


def discover_mem_vmalloc(section):
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
        human_readable_func=lambda v: f"{v:.1f} MB",
        infoname="Used",
        boundaries=(0, total_mb),
    )
    yield check_levels(
        chunk_mb,
        dsname="chunk",
        params=(None, None) + params["levels_lower_chunk_mb"],
        human_readable_func=lambda v: f"{v:.1f} MB",
        infoname="Largest chunk",
        boundaries=(0, total_mb),
    )


check_info["mem.vmalloc"] = LegacyCheckDefinition(
    name="mem_vmalloc",
    service_name="Vmalloc address space",
    sections=["mem"],
    discovery_function=discover_mem_vmalloc,
    check_function=check_mem_vmalloc,
    check_default_parameters={
        "levels_used_perc": (80.0, 90.0),
        "levels_lower_chunk_mb": (64, 32),
    },
)
