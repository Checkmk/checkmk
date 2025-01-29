#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.poe import check_poe_data, PoeStatus, PoeValues
from cmk.plugins.lib.tplink import DETECT_TPLINK

Section = Mapping[str, PoeValues]


# Maps poe power status to faulty status detail string.
# See tpPoePowerStatus in TPLINK-POWER-OVER-ETHERNET-MIB
poe_faulty_status_to_string = {
    "3": "overload",
    "4": "short",
    "5": "nonstandard-pd",
    "6": "voltage-high",
    "7": "voltage-low",
    "8": "hardware-fault",
    "9": "overtemperature",
}


def _deci_watt_to_watt(deci_watt):
    """Convert from deci watt to watt"""
    return float(deci_watt) / 10


def parse_tplink_poe(string_table: Sequence[StringTable]) -> Section:
    """
    parse string_table data and create dictionary with namedtuples for each item.

    {
       item : PoeData(poe_max, poe_used, pse_op_status)
    }

    :param string_table: parsed snmp data
    :return: dictionary
    """
    interface_list, poe_info = string_table

    poe_dict = {}
    for port_index, poe_port_status, poe_max, poe_used, poe_power_status in poe_info:
        try:
            # port_index is the 1 based port number not the interface index.
            # But we can use this number to index the list of interfaces.
            interface_index = int(port_index) - 1
            item = interface_list[interface_index][0]
            poe_status = PoeStatus.FAULTY
            poe_status_detail = None

            if poe_port_status == "1":
                # poe feature enabled for port
                if poe_power_status == "0":  # status: off
                    poe_status = PoeStatus.OFF
                elif poe_power_status == "1":  # status: turning-on
                    poe_status = PoeStatus.OFF
                elif poe_power_status == "2":  # status: on
                    poe_status = PoeStatus.ON
                else:
                    # Some faulty status. Try to map status detail string
                    poe_status_detail = poe_faulty_status_to_string.get(poe_power_status, None)
            else:
                # poe feature disabled for port
                continue

            poe_dict[item] = PoeValues(
                poe_max=_deci_watt_to_watt(poe_max),
                poe_used=_deci_watt_to_watt(poe_used),
                poe_status=poe_status,
                poe_status_detail=poe_status_detail,
            )
        except (ValueError, IndexError):
            pass
    return poe_dict


def discover_tplink_poe(section: Section) -> DiscoveryResult:
    yield from [Service(item=item) for item in section]


def check_tplink_poe(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (poe_data := section.get(item)):
        return
    yield from check_poe_data(params, poe_data)


snmp_section_tplink_poe = SNMPSection(
    name="tplink_poe",
    detect=DETECT_TPLINK,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.2.2.1",
            oids=["1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.11863.6.56.1.1.2.1.1",
            oids=["1", "2", "4", "7", "11"],
        ),
    ],
    parse_function=parse_tplink_poe,
)
check_plugin_tplink_poe = CheckPlugin(
    name="tplink_poe",
    service_name="POE%s consumption",
    discovery_function=discover_tplink_poe,
    check_function=check_tplink_poe,
    check_default_parameters={"levels": ("fixed", (90.0, 95.0))},
)
