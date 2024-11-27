#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Defined by customer, see SUP-1020


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import contains, render, SNMPTree

check_info = {}


def parse_huawei_wlc_devs(string_table):
    parsed = {}

    # Devices
    for name, cpu_perc, mem_perc in string_table:
        if name:
            parsed[name] = {}
            for metric, value in (("cpu_percent", cpu_perc), ("mem_used_percent", mem_perc)):
                parsed[name][metric] = float(value)

    return parsed


check_info["huawei_wlc_devs"] = LegacyCheckDefinition(
    name="huawei_wlc_devs",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2011.2.240.17"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2011.5.25.31.1.1",
        oids=["2.1.13", "1.1.5", "1.1.7"],
    ),
    parse_function=parse_huawei_wlc_devs,
)


def discovery_huawei_wlc_devs_mem(parsed):
    for name, dev in parsed.items():
        if dev["mem_used_percent"] is not None:
            yield name, {}


def check_huawei_wlc_devs_mem(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    lev = params.get("levels")
    val = data.get("%s" % "mem_used_percent")

    yield check_levels(
        val,
        "mem_used_percent",
        lev,
        human_readable_func=render.percent,
        infoname="Used",
    )


check_info["huawei_wlc_devs.mem"] = LegacyCheckDefinition(
    name="huawei_wlc_devs_mem",
    service_name="Device %s Memory",
    sections=["huawei_wlc_devs"],
    discovery_function=discovery_huawei_wlc_devs_mem,
    check_function=check_huawei_wlc_devs_mem,
    check_default_parameters={"levels": (80.0, 90.0)},
)


def discovery_huawei_wlc_devs_cpu(parsed):
    for name, dev in parsed.items():
        if dev["cpu_percent"] is not None:
            yield name, {}


def check_huawei_wlc_devs_cpu(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    lev = params.get("levels")
    val = data.get("%s" % "cpu_percent")

    yield check_levels(
        val, "cpu_percent", lev, human_readable_func=render.percent, infoname="Usage"
    )


check_info["huawei_wlc_devs.cpu"] = LegacyCheckDefinition(
    name="huawei_wlc_devs_cpu",
    service_name="Device %s CPU",
    sections=["huawei_wlc_devs"],
    discovery_function=discovery_huawei_wlc_devs_cpu,
    check_function=check_huawei_wlc_devs_cpu,
    check_default_parameters={"levels": (80.0, 90.0)},
)
