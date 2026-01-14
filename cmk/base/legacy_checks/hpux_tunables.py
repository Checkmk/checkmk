#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"

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

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def parse_hpux_tunables(info):
    parsed = {}
    for line in info:
        if "Tunable" in line[0] or "Parameter" in line[0]:
            key = line[1].strip()
        elif "Usage" in line[0]:
            usage = int(line[1])
        elif "Setting" in line[0]:
            threshold = int(line[1])

            parsed[key] = (usage, threshold)

    return parsed


check_info["hpux_tunables"] = LegacyCheckDefinition(
    name="hpux_tunables",
    parse_function=parse_hpux_tunables,
)


def inventory_hpux_tunables(section, tunable):
    if tunable in section:
        return [(None, {})]
    return []


def check_hpux_tunables(section, params, tunable, descr):
    if tunable in section:
        usage, threshold = section[tunable]
        perc = float(usage) / float(threshold) * 100

        if isinstance(params, tuple):
            params = {
                "levels": params,
            }
        warn, crit = params["levels"]
        warn_perf = float(warn * threshold / 100)
        crit_perf = float(crit * threshold / 100)

        yield (
            0,
            "%.2f%% used (%d/%d %s)" % (perc, usage, threshold, descr),
            [(descr, usage, warn_perf, crit_perf, 0, threshold)],
        )

        if perc > crit:
            state = 2
        elif perc > warn:
            state = 1
        else:
            state = 0

        if state > 0:
            yield state, f"(warn/crit at {warn}/{crit})"

    else:
        yield 3, "tunable not found in agent output"


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


def discover_hpux_tunables_nkthread(section):
    tunable = "nkthread"
    return inventory_hpux_tunables(section, tunable)


def check_hpux_tunables_nkthread(_no_item, params, section):
    tunable = "nkthread"
    descr = "threads"
    return check_hpux_tunables(section, params, tunable, descr)


check_info["hpux_tunables.nkthread"] = LegacyCheckDefinition(
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


def discover_hpux_tunables_nproc(section):
    tunable = "nproc"
    return inventory_hpux_tunables(section, tunable)


def check_hpux_tunables_nproc(_no_item, params, section):
    tunable = "nproc"
    descr = "processes"
    return check_hpux_tunables(section, params, tunable, descr)


check_info["hpux_tunables.nproc"] = LegacyCheckDefinition(
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


def discover_hpux_tunables_maxfiles_lim(section):
    tunable = "maxfiles_lim"
    return inventory_hpux_tunables(section, tunable)


def check_hpux_tunables_maxfiles_lim(_no_item, params, section):
    tunable = "maxfiles_lim"
    descr = "files"
    return check_hpux_tunables(section, params, tunable, descr)


check_info["hpux_tunables.maxfiles_lim"] = LegacyCheckDefinition(
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


def discover_hpux_tunables_semmni(section):
    tunable = "semmni"
    return inventory_hpux_tunables(section, tunable)


def check_hpux_tunables_semmni(_no_item, params, section):
    tunable = "semmni"
    descr = "semaphore_ids"
    return check_hpux_tunables(section, params, tunable, descr)


check_info["hpux_tunables.semmni"] = LegacyCheckDefinition(
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


def discover_hpux_tunables_shmseg(section):
    tunable = "shmseg"
    return inventory_hpux_tunables(section, tunable)


def check_hpux_tunables_shmseg(_no_item, params, section):
    tunable = "shmseg"
    descr = "segments"
    return check_hpux_tunables(section, params, tunable, descr)


check_info["hpux_tunables.shmseg"] = LegacyCheckDefinition(
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


def discover_hpux_tunables_semmns(section):
    tunable = "semmns"
    return inventory_hpux_tunables(section, tunable)


def check_hpux_tunables_semmns(_no_item, params, section):
    tunable = "semmns"
    descr = "entries"
    return check_hpux_tunables(section, params, tunable, descr)


check_info["hpux_tunables.semmns"] = LegacyCheckDefinition(
    name="hpux_tunables_semmns",
    service_name="Number of IPC Semaphores",
    sections=["hpux_tunables"],
    discovery_function=discover_hpux_tunables_semmns,
    check_function=check_hpux_tunables_semmns,
    check_default_parameters={"levels": (85.0, 90.0)},
)
