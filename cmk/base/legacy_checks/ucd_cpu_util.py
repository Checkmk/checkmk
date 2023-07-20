#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util_unix, CPUInfo
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import get_rate, get_value_store, SNMPTree
from cmk.base.plugins.agent_based.utils import ucd_hr_detection

#    UCD-SNMP-MIB::ssCpuRawUser.0 = Counter32: 219998591
#    UCD-SNMP-MIB::ssCpuRawNice.0 = Counter32: 0
#    UCD-SNMP-MIB::ssCpuRawSystem.0 = Counter32: 98206536
#    UCD-SNMP-MIB::ssCpuRawIdle.0 = Counter32: 3896034232
#    UCD-SNMP-MIB::ssCpuRawWait.0 = Counter32: 325152257
#    UCD-SNMP-MIB::ssCpuRawInterrupt.0 = Counter32: 1940759
#    UCD-SNMP-MIB::ssIORawSent.0 = Counter32: 898622850
#    UCD-SNMP-MIB::ssIORawReceived.0 = Counter32: 445747508
#    UCD-SNMP-MIB::ssCpuRawSoftIRQ.0 = Counter32: 277402


def parse_ucd_cpu_util(string_table):
    if not string_table:
        return {}

    (
        error,
        raw_cpu_user,
        raw_cpu_nice,
        raw_cpu_system,
        raw_cpu_idle,
        raw_cpu_wait,
        raw_cpu_interrupt,
        raw_io_send,
        raw_io_received,
        raw_cpu_softirq,
    ) = string_table[0]

    raw_cpu_ticks = [
        raw_cpu_user or None,
        raw_cpu_nice or None,
        raw_cpu_system or None,
        raw_cpu_idle or None,
        raw_cpu_wait or None,
        raw_cpu_interrupt or None,
        raw_cpu_softirq or None,
    ]

    try:
        return {
            "error": error or None,
            "cpu_ticks": CPUInfo("cpu", *raw_cpu_ticks),
            "raw_io_send": raw_io_send,
            "raw_io_received": raw_io_received,
        }
    except ValueError:
        return None


def inventory_ucd_cpu_util(info):
    if info:
        yield None, {}


def check_ucd_cpu_util(item, params, parsed):
    now = time.time()
    value_store = get_value_store()
    error = parsed["error"]
    if error is not None and error != "systemStats":
        yield 1, "Error: %s" % error

    cpu_ticks = parsed["cpu_ticks"]
    for result in check_cpu_util_unix(cpu_ticks, params):
        yield result

    try:
        raw_io_received = int(parsed["raw_io_received"])
        raw_io_send = int(parsed["raw_io_send"])
    except ValueError:
        return

    perfdata = [
        ("read_blocks", get_rate(value_store, "io_received", now, raw_io_received), None, None),
        ("write_blocks", get_rate(value_store, "io_send", now, raw_io_send), None, None),
    ]
    yield 0, "", perfdata


check_info["ucd_cpu_util"] = LegacyCheckDefinition(
    detect=ucd_hr_detection.PREFER_HR_ELSE_UCD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2021.11",
        oids=["2", "50", "51", "52", "53", "54", "56", "57", "58", "61"],
    ),
    parse_function=parse_ucd_cpu_util,
    service_name="CPU utilization",
    discovery_function=inventory_ucd_cpu_util,
    check_function=check_ucd_cpu_util,
    check_ruleset_name="cpu_iowait",
)
