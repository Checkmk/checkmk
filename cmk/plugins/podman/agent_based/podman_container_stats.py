#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


import json
from collections.abc import Mapping

from cmk.agent_based.v2 import AgentSection, StringTable

from .lib import SectionPodmanContainerStats

_BYTE_UNITS: Mapping[str, float] = {
    "kB": 1e3,
    "MB": 1e6,
    "GB": 1e9,
    "TB": 1e12,
    "B": 1,
}


def _parse_byte_string(raw: str) -> int:
    raw = raw.strip()
    for suffix, factor in _BYTE_UNITS.items():
        if raw.endswith(suffix):
            return int(float(raw[: -len(suffix)]) * factor)
    raise ValueError(f"Unknown byte unit in {raw!r}")


def _normalize_cli_stats(data: Mapping[str, object]) -> Mapping[str, object]:
    cpu_percent = str(data.get("cpu_percent", "0%")).rstrip("%")

    mem_parts = str(data.get("mem_usage", "0B / 0B")).split(" / ")
    mem_usage = _parse_byte_string(mem_parts[0])
    mem_limit = _parse_byte_string(mem_parts[1]) if len(mem_parts) > 1 else 0

    block_parts = str(data.get("block_io", "0B / 0B")).split(" / ")
    block_input = _parse_byte_string(block_parts[0])
    block_output = _parse_byte_string(block_parts[1]) if len(block_parts) > 1 else 0

    return {
        "CPU": float(cpu_percent),
        "MemUsage": mem_usage,
        "MemLimit": mem_limit,
        "BlockInput": block_input,
        "BlockOutput": block_output,
    }


def parse_podman_container_stats(
    string_table: StringTable,
) -> SectionPodmanContainerStats | None:
    if not string_table[0]:
        return None

    raw = json.loads(string_table[0][0])

    if "cpu_percent" in raw:
        raw = _normalize_cli_stats(raw)

    return SectionPodmanContainerStats.model_validate(raw)


agent_section_podman_container_stats: AgentSection = AgentSection(
    name="podman_container_stats",
    parse_function=parse_podman_container_stats,
)
