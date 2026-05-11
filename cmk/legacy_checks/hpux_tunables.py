#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<hpux_tunables:sep(58)>>>
# Tunable:        dbc_max_pct
# Usage:          0
# Setting:        1
# Percentage:     0.0
#
# Tunable:        maxdsiz
# Usage:          176676864
# Setting:        1073741824
# Percentage:     16.5

# Example of parsed:
#
# {'dbc_max_pct' : (0, 1),
#  'maxdsiz'     : (176676864, 1073741824),
# }

# .
#   .--general functions---------------------------------------------------.
#   |                                                  _                   |
#   |                   __ _  ___ _ __   ___ _ __ __ _| |                  |
#   |                  / _` |/ _ \ '_ \ / _ \ '__/ _` | |                  |
#   |                 | (_| |  __/ | | |  __/ | | (_| | |                  |
#   |                  \__, |\___|_| |_|\___|_|  \__,_|_|                  |
#   |                  |___/                                               |
#   |              __                  _   _                               |
#   |             / _|_   _ _ __   ___| |_(_) ___  _ __  ___               |
#   |            | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|              |
#   |            |  _| |_| | | | | (__| |_| | (_) | | | \__ \              |
#   |            |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

Section = dict[str, tuple[int, int]]


def parse_hpux_tunables(string_table: StringTable) -> Section:
    parsed: Section = {}
    key = ""
    usage = 0
    for line in string_table:
        if "Tunable" in line[0] or "Parameter" in line[0]:
            key = line[1].strip()
        elif "Usage" in line[0]:
            usage = int(line[1])
        elif "Setting" in line[0]:
            threshold = int(line[1])
            parsed[key] = (usage, threshold)

    return parsed


agent_section_hpux_tunables = AgentSection(
    name="hpux_tunables",
    parse_function=parse_hpux_tunables,
)


def _discover_tunable(section: Section, tunable: str) -> DiscoveryResult:
    if tunable in section:
        yield Service()


def _check_tunable(
    section: Section, params: Mapping[str, Any], tunable: str, descr: str
) -> CheckResult:
    if tunable not in section:
        yield Result(state=State.UNKNOWN, summary="tunable not found in agent output")
        return

    usage, threshold = section[tunable]
    perc = float(usage) / float(threshold) * 100

    warn, crit = params["levels"]
    warn_perf = float(warn * threshold / 100)
    crit_perf = float(crit * threshold / 100)

    yield Result(state=State.OK, summary=f"{perc:.2f}% used ({usage}/{threshold} {descr})")
    yield Metric(descr, usage, levels=(warn_perf, crit_perf), boundaries=(0, threshold))

    if perc > crit:
        yield Result(state=State.CRIT, summary=f"(warn/crit at {warn}/{crit})")
    elif perc > warn:
        yield Result(state=State.WARN, summary=f"(warn/crit at {warn}/{crit})")


# .
#   .--nkthread------------------------------------------------------------.
#   |                    _    _   _                        _               |
#   |              _ __ | | _| |_| |__  _ __ ___  __ _  __| |              |
#   |             | '_ \| |/ / __| '_ \| '__/ _ \/ _` |/ _` |              |
#   |             | | | |   <| |_| | | | | |  __/ (_| | (_| |              |
#   |             |_| |_|_|\_\\__|_| |_|_|  \___|\__,_|\__,_|              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_hpux_tunables_nkthread(section: Section) -> DiscoveryResult:
    yield from _discover_tunable(section, "nkthread")


def check_hpux_tunables_nkthread(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from _check_tunable(section, params, "nkthread", "threads")


check_plugin_hpux_tunables_nkthread = CheckPlugin(
    name="hpux_tunables_nkthread",
    service_name="Number of threads",
    sections=["hpux_tunables"],
    discovery_function=discover_hpux_tunables_nkthread,
    check_function=check_hpux_tunables_nkthread,
    check_default_parameters={
        "levels": (80.0, 85.0),
    },
)

# .
#   .--nproc---------------------------------------------------------------.
#   |                                                                      |
#   |                     _ __  _ __  _ __ ___   ___                       |
#   |                    | '_ \| '_ \| '__/ _ \ / __|                      |
#   |                    | | | | |_) | | | (_) | (__                       |
#   |                    |_| |_| .__/|_|  \___/ \___|                      |
#   |                          |_|                                         |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_hpux_tunables_nproc(section: Section) -> DiscoveryResult:
    yield from _discover_tunable(section, "nproc")


def check_hpux_tunables_nproc(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from _check_tunable(section, params, "nproc", "processes")


check_plugin_hpux_tunables_nproc = CheckPlugin(
    name="hpux_tunables_nproc",
    service_name="Number of processes",
    sections=["hpux_tunables"],
    discovery_function=discover_hpux_tunables_nproc,
    check_function=check_hpux_tunables_nproc,
    check_default_parameters={"levels": (90.0, 96.0)},
)

# .
#   .--maxfiles_lim--------------------------------------------------------.
#   |                            __ _ _               _ _                  |
#   |      _ __ ___   __ ___  __/ _(_) | ___  ___    | (_)_ __ ___         |
#   |     | '_ ` _ \ / _` \ \/ / |_| | |/ _ \/ __|   | | | '_ ` _ \        |
#   |     | | | | | | (_| |>  <|  _| | |  __/\__ \   | | | | | | | |       |
#   |     |_| |_| |_|\__,_/_/\_\_| |_|_|\___||___/___|_|_|_| |_| |_|       |
#   |                                           |_____|                    |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_hpux_tunables_maxfiles_lim(section: Section) -> DiscoveryResult:
    yield from _discover_tunable(section, "maxfiles_lim")


def check_hpux_tunables_maxfiles_lim(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from _check_tunable(section, params, "maxfiles_lim", "files")


check_plugin_hpux_tunables_maxfiles_lim = CheckPlugin(
    name="hpux_tunables_maxfiles_lim",
    service_name="Number of open files",
    sections=["hpux_tunables"],
    discovery_function=discover_hpux_tunables_maxfiles_lim,
    check_function=check_hpux_tunables_maxfiles_lim,
    check_default_parameters={"levels": (85.0, 90.0)},
)

# .
#   .--semmni--------------------------------------------------------------.
#   |                                                   _                  |
#   |                ___  ___ _ __ ___  _ __ ___  _ __ (_)                 |
#   |               / __|/ _ \ '_ ` _ \| '_ ` _ \| '_ \| |                 |
#   |               \__ \  __/ | | | | | | | | | | | | | |                 |
#   |               |___/\___|_| |_| |_|_| |_| |_|_| |_|_|                 |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_hpux_tunables_semmni(section: Section) -> DiscoveryResult:
    yield from _discover_tunable(section, "semmni")


def check_hpux_tunables_semmni(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from _check_tunable(section, params, "semmni", "semaphore_ids")


check_plugin_hpux_tunables_semmni = CheckPlugin(
    name="hpux_tunables_semmni",
    service_name="Number of IPC Semaphore IDs",
    sections=["hpux_tunables"],
    discovery_function=discover_hpux_tunables_semmni,
    check_function=check_hpux_tunables_semmni,
    check_default_parameters={"levels": (85.0, 90.0)},
)

# .
#   .--shmseg--------------------------------------------------------------.
#   |                     _                                                |
#   |                 ___| |__  _ __ ___  ___  ___  __ _                   |
#   |                / __| '_ \| '_ ` _ \/ __|/ _ \/ _` |                  |
#   |                \__ \ | | | | | | | \__ \  __/ (_| |                  |
#   |                |___/_| |_|_| |_| |_|___/\___|\__, |                  |
#   |                                              |___/                   |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_hpux_tunables_shmseg(section: Section) -> DiscoveryResult:
    yield from _discover_tunable(section, "shmseg")


def check_hpux_tunables_shmseg(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from _check_tunable(section, params, "shmseg", "segments")


check_plugin_hpux_tunables_shmseg = CheckPlugin(
    name="hpux_tunables_shmseg",
    service_name="Number of shared memory segments",
    sections=["hpux_tunables"],
    discovery_function=discover_hpux_tunables_shmseg,
    check_function=check_hpux_tunables_shmseg,
    check_default_parameters={"levels": (85.0, 90.0)},
)

# .
#   .--semmns--------------------------------------------------------------.
#   |                                                                      |
#   |               ___  ___ _ __ ___  _ __ ___  _ __  ___                 |
#   |              / __|/ _ \ '_ ` _ \| '_ ` _ \| '_ \/ __|                |
#   |              \__ \  __/ | | | | | | | | | | | | \__ \                |
#   |              |___/\___|_| |_| |_|_| |_| |_|_| |_|___/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_hpux_tunables_semmns(section: Section) -> DiscoveryResult:
    yield from _discover_tunable(section, "semmns")


def check_hpux_tunables_semmns(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from _check_tunable(section, params, "semmns", "entries")


check_plugin_hpux_tunables_semmns = CheckPlugin(
    name="hpux_tunables_semmns",
    service_name="Number of IPC Semaphores",
    sections=["hpux_tunables"],
    discovery_function=discover_hpux_tunables_semmns,
    check_function=check_hpux_tunables_semmns,
    check_default_parameters={"levels": (85.0, 90.0)},
)
