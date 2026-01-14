#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.base.check_legacy_includes.ddn_s2a import parse_ddn_s2a_api_response

check_info = {}


def parse_ddn_s2a_stats(string_table):
    return {
        key: value[0] if key.startswith("All_ports") else value
        for key, value in parse_ddn_s2a_api_response(string_table).items()
    }


#   .--Read hits-----------------------------------------------------------.
#   |               ____                _   _     _ _                      |
#   |              |  _ \ ___  __ _  __| | | |__ (_) |_ ___                |
#   |              | |_) / _ \/ _` |/ _` | | '_ \| | __/ __|               |
#   |              |  _ <  __/ (_| | (_| | | | | | | |_\__ \               |
#   |              |_| \_\___|\__,_|\__,_| |_| |_|_|\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_stats_readhits(parsed):
    if "All_ports_Read_Hits" in parsed:
        yield "Total", {}
    for nr, _ in enumerate(parsed.get("Read_Hits", [])):
        yield "%d" % (nr + 1), {}


def check_ddn_s2a_stats_readhits(item, params, parsed):
    if item == "Total":
        read_hits = float(parsed["All_ports_Read_Hits"])
    else:
        read_hits = float(parsed["Read_Hits"][int(item) - 1])

    return check_levels(
        read_hits,
        "read_hits",
        (None, None) + params["levels_lower"],
        human_readable_func=render.percent,
    )


check_info["ddn_s2a_stats.readhits"] = LegacyCheckDefinition(
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


def discover_ddn_s2a_stats_io(parsed):
    if "All_ports_Read_IOs" in parsed:
        yield "Total", {}
    for nr, _ in enumerate(parsed.get("Read_IOs", [])):
        yield "%d" % (nr + 1), {}


def check_ddn_s2a_stats_io(item, params, parsed):
    def check_io_levels(value, levels, infotext_formatstring, perfname=None):
        infotext = infotext_formatstring % value
        if levels is None:
            return (0, infotext) if perfname is None else (0, infotext, [(perfname, value)])

        warn, crit = levels
        perfdata = [(perfname, value, warn, crit)]
        levelstext = f" (warn/crit at {warn:.2f}/{crit:.2f} 1/s)"
        if value >= crit:
            status = 2
            infotext += levelstext
        elif value >= warn:
            status = 1
            infotext += levelstext
        else:
            status = 0

        if perfname is None:
            return status, infotext
        return status, infotext, perfdata

    if item == "Total":
        read_ios_s = float(parsed["All_ports_Read_IOs"])
        write_ios_s = float(parsed["All_ports_Write_IOs"])
    else:
        read_ios_s = float(parsed["Read_IOs"][int(item) - 1])
        write_ios_s = float(parsed["Write_IOs"][int(item) - 1])
    total_ios_s = read_ios_s + write_ios_s

    yield check_io_levels(read_ios_s, params.get("read"), "Read: %.2f 1/s", "disk_read_ios")
    yield check_io_levels(write_ios_s, params.get("write"), "Write: %.2f 1/s", "disk_write_ios")
    yield check_io_levels(total_ios_s, params.get("total"), "Total: %.2f 1/s")


check_info["ddn_s2a_stats.io"] = LegacyCheckDefinition(
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


def discover_ddn_s2a_stats(parsed):
    if "All_ports_Read_MBs" in parsed:
        yield "Total", {}
    for nr, _value in enumerate(parsed.get("Read_MBs", [])):
        yield "%d" % (nr + 1), {}


def check_ddn_s2a_stats(item, params, parsed):
    def check_datarate_levels(value, value_mb, levels, infotext_formatstring, perfname=None):
        infotext = infotext_formatstring % value_mb
        if levels is None:
            return (0, infotext) if perfname is None else (0, infotext, [(perfname, value)])

        warn, crit = levels
        warn_mb, crit_mb = (x / (1024 * 1024.0) for x in levels)
        perfdata = [(perfname, value, warn, crit)]
        levelstext = f" (warn/crit at {warn_mb:.2f}/{crit_mb:.2f} MB/s)"
        if value >= crit:
            status = 2
            infotext += levelstext
        elif value >= warn:
            status = 1
            infotext += levelstext
        else:
            status = 0

        if perfname is None:
            return status, infotext
        return status, infotext, perfdata

    if item == "Total":
        read_mb_s = float(parsed["All_ports_Read_MBs"])
        write_mb_s = float(parsed["All_ports_Write_MBs"])
    else:
        read_mb_s = float(parsed["Read_MBs"][int(item) - 1])
        write_mb_s = float(parsed["Write_MBs"][int(item) - 1])
    total_mb_s = read_mb_s + write_mb_s
    read = read_mb_s * 1024 * 1024
    write = write_mb_s * 1024 * 1024
    total = total_mb_s * 1024 * 1024

    yield check_datarate_levels(
        read, read_mb_s, params.get("read"), "Read: %.2f MB/s", "disk_read_throughput"
    )
    yield check_datarate_levels(
        write, write_mb_s, params.get("write"), "Write: %.2f MB/s", "disk_write_throughput"
    )
    yield check_datarate_levels(total, total_mb_s, params.get("total"), "Total: %.2f MB/s")


check_info["ddn_s2a_stats"] = LegacyCheckDefinition(
    name="ddn_s2a_stats",
    parse_function=parse_ddn_s2a_stats,
    service_name="DDN S2A Data Rate %s",
    discovery_function=discover_ddn_s2a_stats,
    check_function=check_ddn_s2a_stats,
    check_ruleset_name="storage_throughput",
    check_default_parameters={
        "total": (4800 * 1024 * 1024, 5500 * 1024 * 1024),
    },
)
