#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#   .--Common--------------------------------------------------------------.
#   |              ____                                                    |
#   |             / ___|___  _ __ ___  _ __ ___   ___  _ __                |
#   |            | |   / _ \| '_ ` _ \| '_ ` _ \ / _ \| '_ \               |
#   |            | |__| (_) | | | | | | | | | | | (_) | | | |              |
#   |             \____\___/|_| |_| |_|_| |_| |_|\___/|_| |_|              |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def arbor_test_threshold(perc, name, warn, crit):
    status = perc > crit and 2 or perc > warn and 1 or 0
    infotext = "%s used: %d%%" % (name, perc)

    if status > 0:
        infotext += " (warn/crit at %.1f%%/%.1f%%) (%s)" % (warn, crit, "!" * status)
    return status, infotext


# .
#   .--Memory--------------------------------------------------------------.
#   |               __  __                                                 |
#   |              |  \/  | ___ _ __ ___   ___  _ __ _   _                 |
#   |              | |\/| |/ _ \ '_ ` _ \ / _ \| '__| | | |                |
#   |              | |  | |  __/ | | | | | (_) | |  | |_| |                |
#   |              |_|  |_|\___|_| |_| |_|\___/|_|   \__, |                |
#   |                                                |___/                 |
#   '----------------------------------------------------------------------'

ARBOR_MEMORY_CHECK_DEFAULT_PARAMETERS = {
    "levels_ram": ("perc_used", (80.0, 90.0)),
    "levels_swap": ("perc_used", (80.0, 90.0)),
}


def inventory_arbor_memory(parsed):
    if len(parsed) > 0:
        return [(None, {})]
    return []


def check_arbor_memory(no_item, params, parsed):
    def worst_status(*args):
        order = [0, 1, 3, 2]
        return sorted(args, key=lambda x: order[x], reverse=True)[0]

    def combine_infotext(*blocks):
        return ", ".join([b for b in blocks if b])

    ram_perc, swap_perc = map(int, parsed["memory"])

    ram_warn, ram_crit = params["levels_ram"][1]
    swap_warn, swap_crit = params["levels_swap"][1]

    ram_status, ram_info = arbor_test_threshold(ram_perc, "RAM", ram_warn, ram_crit)
    swap_status, swap_info = arbor_test_threshold(swap_perc, "Swap", swap_warn, swap_crit)

    infotext = combine_infotext(ram_info, swap_info)

    perfdata = [
        ("mem_used_percent", ram_perc, ram_warn, ram_crit),
        ("swap_used_percent", swap_perc, swap_warn, swap_crit),
    ]

    return worst_status(ram_status, swap_status), infotext, perfdata


# .
#   .--Disk Usage----------------------------------------------------------.
#   |            ____  _     _      _   _                                  |
#   |           |  _ \(_)___| | __ | | | |___  __ _  __ _  ___             |
#   |           | | | | / __| |/ / | | | / __|/ _` |/ _` |/ _ \            |
#   |           | |_| | \__ \   <  | |_| \__ \ (_| | (_| |  __/            |
#   |           |____/|_|___/_|\_\  \___/|___/\__,_|\__, |\___|            |
#   |                                               |___/                  |
#   '----------------------------------------------------------------------'


def inventory_arbor_disk_usage(parsed):
    if "disk" in parsed:
        return [("/", {})]
    return []


def check_arbor_disk_usage(no_item, params, parsed):
    usage = int(parsed["disk"])
    status, infotext = arbor_test_threshold(usage, "Disk", *params["levels"])
    return status, infotext, [("disk_utilization", float(usage) / 100.0)]


# .
#   .--Host Fault----------------------------------------------------------.
#   |             _   _           _     _____           _ _                |
#   |            | | | | ___  ___| |_  |  ___|_ _ _   _| | |_              |
#   |            | |_| |/ _ \/ __| __| | |_ / _` | | | | | __|             |
#   |            |  _  | (_) \__ \ |_  |  _| (_| | |_| | | |_              |
#   |            |_| |_|\___/|___/\__| |_|  \__,_|\__,_|_|\__|             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_arbor_host_fault(parsed):
    if "host_fault" in parsed:
        return [(None, None)]
    return []


def check_arbor_host_fault(no_item, no_params, parsed):
    status = 0
    if parsed["host_fault"] != "No Fault":
        status = 2
    return status, parsed["host_fault"]


# .
#   .--Drop Rate-----------------------------------------------------------.
#   |             ____                    ____       _                     |
#   |            |  _ \ _ __ ___  _ __   |  _ \ __ _| |_ ___               |
#   |            | | | | '__/ _ \| '_ \  | |_) / _` | __/ _ \              |
#   |            | |_| | | | (_) | |_) | |  _ < (_| | ||  __/              |
#   |            |____/|_|  \___/| .__/  |_| \_\__,_|\__\___|              |
#   |                            |_|                                       |
#   '----------------------------------------------------------------------'


def inventory_arbor_drop_rate(parsed):
    if "drop_rate" in parsed:
        return [("Overrun", {})]
    return []


def check_arbor_drop_rate(no_item, params, parsed):
    drop_rate = int(parsed["drop_rate"])
    infotext = "%s pps" % drop_rate

    lower_status = 0
    lower_levels = params.get("levels_lower")
    if lower_levels:
        warn, crit = lower_levels

        if drop_rate <= crit:
            lower_status, label = 2, "(!!)"
        elif drop_rate <= warn:
            lower_status, label = 1, "(!)"

        if lower_status:
            infotext += " (warn/crit below %.1f/%.1f)%s" % (warn, crit, label)

    upper_status = 0
    upper_levels = params.get("levels")
    if upper_levels:
        warn, crit = upper_levels

        if drop_rate >= crit:
            upper_status, label = 2, "(!!)"
        elif drop_rate >= warn:
            upper_status, label = 1, "(!)"

        if upper_status:
            infotext += " (warn/crit above %.1f/%.1f)%s" % (warn, crit, label)

        perfdata: list[tuple] = [("if_in_pkts", drop_rate, warn, crit)]
    else:
        perfdata = [("if_in_pkts", drop_rate)]

    status = max(lower_status, upper_status)
    yield status, infotext, perfdata


# .
