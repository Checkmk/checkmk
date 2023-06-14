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

# For legacy reasons we need to keep the old format:


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


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


def inventory_hpux_tunables(info, tunable):
    if tunable in parse_hpux_tunables(info):
        return [(None, {})]
    return []


def check_hpux_tunables(info, params, tunable, descr):
    # Since the original author forgot to implement a
    # main check (without dot) we cannot declare parse
    # function in check_info...
    parsed = parse_hpux_tunables(info)

    if tunable in parsed:
        usage, threshold = parsed[tunable]
        perc = float(usage) / float(threshold) * 100

        if isinstance(params, tuple):
            params = {
                "levels": params,
            }
        warn, crit = params["levels"]
        warn_perf = float(warn * threshold / 100)
        crit_perf = float(crit * threshold / 100)

        yield 0, "%.2f%% used (%d/%d %s)" % (perc, usage, threshold, descr), [
            (descr, usage, warn_perf, crit_perf, 0, threshold)
        ]

        if perc > crit:
            state = 2
        elif perc > warn:
            state = 1
        else:
            state = 0

        if state > 0:
            yield state, "(warn/crit at %s/%s)" % (warn, crit)

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


def inventory_hpux_tunables_nkthread(info):
    tunable = "nkthread"
    return inventory_hpux_tunables(info, tunable)


def check_hpux_tunables_nkthread(_no_item, params, info):
    tunable = "nkthread"
    descr = "threads"
    return check_hpux_tunables(info, params, tunable, descr)


check_info["hpux_tunables.nkthread"] = LegacyCheckDefinition(
    discovery_function=inventory_hpux_tunables_nkthread,
    check_function=check_hpux_tunables_nkthread,
    service_name="Number of threads",
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


def inventory_hpux_tunables_nproc(info):
    tunable = "nproc"
    return inventory_hpux_tunables(info, tunable)


def check_hpux_tunables_nproc(_no_item, params, info):
    tunable = "nproc"
    descr = "processes"
    return check_hpux_tunables(info, params, tunable, descr)


check_info["hpux_tunables.nproc"] = LegacyCheckDefinition(
    discovery_function=inventory_hpux_tunables_nproc,
    check_function=check_hpux_tunables_nproc,
    service_name="Number of processes",
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


def inventory_hpux_tunables_maxfiles_lim(info):
    tunable = "maxfiles_lim"
    return inventory_hpux_tunables(info, tunable)


def check_hpux_tunables_maxfiles_lim(_no_item, params, info):
    tunable = "maxfiles_lim"
    descr = "files"
    return check_hpux_tunables(info, params, tunable, descr)


check_info["hpux_tunables.maxfiles_lim"] = LegacyCheckDefinition(
    discovery_function=inventory_hpux_tunables_maxfiles_lim,
    check_function=check_hpux_tunables_maxfiles_lim,
    service_name="Number of open files",
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


def inventory_hpux_tunables_semmni(info):
    tunable = "semmni"
    return inventory_hpux_tunables(info, tunable)


def check_hpux_tunables_semmni(_no_item, params, info):
    tunable = "semmni"
    descr = "semaphore_ids"
    return check_hpux_tunables(info, params, tunable, descr)


check_info["hpux_tunables.semmni"] = LegacyCheckDefinition(
    discovery_function=inventory_hpux_tunables_semmni,
    check_function=check_hpux_tunables_semmni,
    service_name="Number of IPC Semaphore IDs",
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


def inventory_hpux_tunables_shmseg(info):
    tunable = "shmseg"
    return inventory_hpux_tunables(info, tunable)


def check_hpux_tunables_shmseg(_no_item, params, info):
    tunable = "shmseg"
    descr = "segments"
    return check_hpux_tunables(info, params, tunable, descr)


check_info["hpux_tunables.shmseg"] = LegacyCheckDefinition(
    discovery_function=inventory_hpux_tunables_shmseg,
    check_function=check_hpux_tunables_shmseg,
    service_name="Number of shared memory segments",
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


def inventory_hpux_tunables_semmns(info):
    tunable = "semmns"
    return inventory_hpux_tunables(info, tunable)


def check_hpux_tunables_semmns(_no_item, params, info):
    tunable = "semmns"
    descr = "entries"
    return check_hpux_tunables(info, params, tunable, descr)


check_info["hpux_tunables.semmns"] = LegacyCheckDefinition(
    discovery_function=inventory_hpux_tunables_semmns,
    check_function=check_hpux_tunables_semmns,
    service_name="Number of IPC Semaphores",
    check_default_parameters={"levels": (85.0, 90.0)},
)
