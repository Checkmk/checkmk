#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib import ucd_hr_detection

check_info = {}

# .1.3.6.1.4.1.2021.2.1.2.1 Web-Processes  --> UCD-SNMP-MIB::prNames.1
# .1.3.6.1.4.1.2021.2.1.2.2 SMTP-Processes --> UCD-SNMP-MIB::prNames.2
# .1.3.6.1.4.1.2021.2.1.2.3 POP3-Processes --> UCD-SNMP-MIB::prNames.3
# .1.3.6.1.4.1.2021.2.1.2.4 LPD-Processes  --> UCD-SNMP-MIB::prNames.4
# .1.3.6.1.4.1.2021.2.1.3.1 5              --> UCD-SNMP-MIB::prMin.1
# .1.3.6.1.4.1.2021.2.1.3.2 1              --> UCD-SNMP-MIB::prMin.2
# .1.3.6.1.4.1.2021.2.1.3.3 1              --> UCD-SNMP-MIB::prMin.3
# .1.3.6.1.4.1.2021.2.1.3.4 1              --> UCD-SNMP-MIB::prMin.4
# .1.3.6.1.4.1.2021.2.1.4.1 50             --> UCD-SNMP-MIB::prMax.1
# .1.3.6.1.4.1.2021.2.1.4.2 800            --> UCD-SNMP-MIB::prMax.2
# .1.3.6.1.4.1.2021.2.1.4.3 800            --> UCD-SNMP-MIB::prMax.3
# .1.3.6.1.4.1.2021.2.1.4.4 800            --> UCD-SNMP-MIB::prMax.4
# .1.3.6.1.4.1.2021.2.1.5.1 11             --> UCD-SNMP-MIB::prCount.1
# .1.3.6.1.4.1.2021.2.1.5.2 1              --> UCD-SNMP-MIB::prCount.2
# .1.3.6.1.4.1.2021.2.1.5.3 1              --> UCD-SNMP-MIB::prCount.3
# .1.3.6.1.4.1.2021.2.1.5.4 1              --> UCD-SNMP-MIB::prCount.4
# .1.3.6.1.4.1.2021.2.1.100.1 0            --> UCD-SNMP-MIB::prErrFlag.1
# .1.3.6.1.4.1.2021.2.1.100.2 0            --> UCD-SNMP-MIB::prErrFlag.2
# .1.3.6.1.4.1.2021.2.1.100.3 0            --> UCD-SNMP-MIB::prErrFlag.3
# .1.3.6.1.4.1.2021.2.1.100.4 0            --> UCD-SNMP-MIB::prErrFlag.4
# .1.3.6.1.4.1.2021.2.1.101.1              --> UCD-SNMP-MIB::prErrMessage.1
# .1.3.6.1.4.1.2021.2.1.101.2              --> UCD-SNMP-MIB::prErrMessage.2
# .1.3.6.1.4.1.2021.2.1.101.3              --> UCD-SNMP-MIB::prErrMessage.3
# .1.3.6.1.4.1.2021.2.1.101.4              --> UCD-SNMP-MIB::prErrMessage.4


def discover_ucd_processes(info):
    return [(line[0].replace("-Processes", ""), None) for line in info]


def check_ucd_processes(item, _no_params, info):
    for pr_name, pr_min_str, pr_max_str, pr_count_str, pr_err_flag, pr_err_msg in info:
        if pr_name.replace("-Processes", "") == item:
            state = 0
            infotext = "Total: %s" % pr_count_str
            if int(pr_err_flag) == 0:
                state = 0
            else:
                state = 2
                if pr_err_msg:
                    infotext += ", %s" % pr_err_msg
                infotext += f" (lower/upper crit at {pr_min_str}/{pr_max_str})"

            return state, infotext, [("processes", int(pr_count_str))]
    return None


def parse_ucd_processes(string_table: StringTable) -> StringTable:
    return string_table


check_info["ucd_processes"] = LegacyCheckDefinition(
    name="ucd_processes",
    parse_function=parse_ucd_processes,
    detect=ucd_hr_detection.PREFER_HR_ELSE_UCD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2021.2.1",
        oids=["2", "3", "4", "5", "100", "101"],
    ),
    service_name="Processes %s",
    discovery_function=discover_ucd_processes,
    check_function=check_ucd_processes,
)
