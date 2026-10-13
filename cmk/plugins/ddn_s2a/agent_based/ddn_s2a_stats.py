#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ddn_s2a.lib import parse_ddn_s2a_api_response


@dataclass(frozen=True, kw_only=True)
class Section:
    totals: Mapping[str, str]
    """Values aggregated over all ports, keyed without the "All_ports_" prefix."""
    per_port: Mapping[str, Sequence[str]]
    """Per port values, one entry per port."""


def parse_ddn_s2a_stats(string_table: StringTable) -> Section:
    parsed = parse_ddn_s2a_api_response(string_table)
    return Section(
        totals={
            key.removeprefix("All_ports_"): value[0]
            for key, value in parsed.items()
            if key.startswith("All_ports_")
        },
        per_port={key: value for key, value in parsed.items() if not key.startswith("All_ports_")},
    )


#   .--Read hits-----------------------------------------------------------.
#   |               ____                _   _     _ _                      |
#   |              |  _ \ ___  __ _  __| | | |__ (_) |_ ___                |
#   |              | |_) / _ \/ _` |/ _` | | '_ \| | __/ __|               |
#   |              |  _ <  __/ (_| | (_| | | | | | | |_\__ \               |
#   |              |_| \_\___|\__,_|\__,_| |_| |_|_|\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_stats_readhits(section: Section) -> DiscoveryResult:
    yield from _discover_ports(section, "Read_Hits")


def check_ddn_s2a_stats_readhits(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (read_hits := _port_value(section, item, "Read_Hits")) is None:
        return

    yield from check_levels(
        read_hits,
        "read_hits",
        (None, None) + params["levels_lower"],
        human_readable_func=render.percent,
    )


check_plugin_ddn_s2a_stats_readhits = CheckPlugin(
    name="ddn_s2a_stats_readhits",
    service_name="DDN S2A Read Hits %s",
    sections=["ddn_s2a_stats"],
    discovery_function=discover_ddn_s2a_stats_readhits,
    check_function=check_ddn_s2a_stats_readhits,
    check_ruleset_name="read_hits",
    check_default_parameters={
        "levels_lower": (85.0, 70.0),
    },
)

# .
#   .--I/O transactions----------------------------------------------------.
#   |                            ___    _____                              |
#   |                           |_ _|  / / _ \                             |
#   |                            | |  / / | | |                            |
#   |                            | | / /| |_| |                            |
#   |                           |___/_/  \___/                             |
#   |                                                                      |
#   |      _                                  _   _                        |
#   |     | |_ _ __ __ _ _ __  ___  __ _  ___| |_(_) ___  _ __  ___        |
#   |     | __| '__/ _` | '_ \/ __|/ _` |/ __| __| |/ _ \| '_ \/ __|       |
#   |     | |_| | | (_| | | | \__ \ (_| | (__| |_| | (_) | | | \__ \       |
#   |      \__|_|  \__,_|_| |_|___/\__,_|\___|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_stats_io(section: Section) -> DiscoveryResult:
    yield from _discover_ports(section, "Read_IOs")


def check_ddn_s2a_stats_io(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    read_ios_s = _port_value(section, item, "Read_IOs")
    write_ios_s = _port_value(section, item, "Write_IOs")
    if read_ios_s is None or write_ios_s is None:
        return

    yield from _check_io_levels("Read", read_ios_s, params.get("read"), "disk_read_ios")
    yield from _check_io_levels("Write", write_ios_s, params.get("write"), "disk_write_ios")
    yield from _check_io_levels("Total", read_ios_s + write_ios_s, params.get("total"), None)


check_plugin_ddn_s2a_stats_io = CheckPlugin(
    name="ddn_s2a_stats_io",
    service_name="DDN S2A IO %s",
    sections=["ddn_s2a_stats"],
    discovery_function=discover_ddn_s2a_stats_io,
    check_function=check_ddn_s2a_stats_io,
    check_ruleset_name="storage_iops",
    check_default_parameters={
        "total": (28000.0, 33000.0),
    },
)

# .
#   .--Data rate-----------------------------------------------------------.
#   |              ____        _                    _                      |
#   |             |  _ \  __ _| |_ __ _   _ __ __ _| |_ ___                |
#   |             | | | |/ _` | __/ _` | | '__/ _` | __/ _ \               |
#   |             | |_| | (_| | || (_| | | | | (_| | ||  __/               |
#   |             |____/ \__,_|\__\__,_| |_|  \__,_|\__\___|               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_stats(section: Section) -> DiscoveryResult:
    yield from _discover_ports(section, "Read_MBs")


def check_ddn_s2a_stats(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    read_mb_s = _port_value(section, item, "Read_MBs")
    write_mb_s = _port_value(section, item, "Write_MBs")
    if read_mb_s is None or write_mb_s is None:
        return

    yield from _check_datarate_levels("Read", read_mb_s, params.get("read"), "disk_read_throughput")
    yield from _check_datarate_levels(
        "Write", write_mb_s, params.get("write"), "disk_write_throughput"
    )
    yield from _check_datarate_levels("Total", read_mb_s + write_mb_s, params.get("total"), None)


def _discover_ports(section: Section, key: str) -> DiscoveryResult:
    if key in section.totals:
        yield Service(item="Total")
    yield from (Service(item=str(nr + 1)) for nr, _ in enumerate(section.per_port.get(key, ())))


def _port_value(section: Section, item: str, key: str) -> float | None:
    if item == "Total":
        raw_value = section.totals.get(key)
    else:
        per_port = section.per_port.get(key, ())
        index = int(item) - 1
        raw_value = per_port[index] if 0 <= index < len(per_port) else None
    return None if raw_value is None else float(raw_value)


def _levels_state(value: float, levels: tuple[float, float] | None) -> State:
    if levels is None:
        return State.OK
    warn, crit = levels
    if value >= crit:
        return State.CRIT
    return State.WARN if value >= warn else State.OK


def _check_io_levels(
    label: str, value: float, levels: tuple[float, float] | None, metric_name: str | None
) -> CheckResult:
    summary = f"{label}: {value:.2f} 1/s"
    if (state := _levels_state(value, levels)) is not State.OK and levels is not None:
        summary += f" (warn/crit at {levels[0]:.2f}/{levels[1]:.2f} 1/s)"

    yield Result(state=state, summary=summary)
    if metric_name is not None:
        yield Metric(metric_name, value, levels=levels)


def _check_datarate_levels(
    label: str, value_mb: float, levels: tuple[float, float] | None, metric_name: str | None
) -> CheckResult:
    # The levels are configured in bytes per second, but we report megabytes per second.
    value = value_mb * 1024 * 1024
    summary = f"{label}: {value_mb:.2f} MB/s"
    if (state := _levels_state(value, levels)) is not State.OK and levels is not None:
        summary += f" (warn/crit at {levels[0] / 1024**2:.2f}/{levels[1] / 1024**2:.2f} MB/s)"

    yield Result(state=state, summary=summary)
    if metric_name is not None:
        yield Metric(metric_name, value, levels=levels)


agent_section_ddn_s2a_stats = AgentSection(
    name="ddn_s2a_stats",
    parse_function=parse_ddn_s2a_stats,
)


check_plugin_ddn_s2a_stats = CheckPlugin(
    name="ddn_s2a_stats",
    service_name="DDN S2A Data Rate %s",
    discovery_function=discover_ddn_s2a_stats,
    check_function=check_ddn_s2a_stats,
    check_ruleset_name="storage_throughput",
    check_default_parameters={
        "total": (4800 * 1024 * 1024, 5500 * 1024 * 1024),
    },
)
