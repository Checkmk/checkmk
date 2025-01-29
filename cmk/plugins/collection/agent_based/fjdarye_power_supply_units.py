#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# check_mk plug-in to monitor Fujitsu storage systems supporting FJDARY-E60.MIB or FJDARY-E100.MIB
# Copyright (c) 2012 FuH Entwicklungsgesellschaft mbH, Umkirch, Germany. All rights reserved.
# Author: Philipp Hoefflin, 2012, hoefflin+cmk@fuh-e.de

# generic data structure widely used in the FJDARY-Mibs:
# <oid>
# <oid>.1: Index
# <oid>.3: Status
# the latter can be one of the following:


from cmk.agent_based.v2 import CheckPlugin, equals, SNMPSection, SNMPTree
from cmk.plugins.lib.fjdarye import check_fjdarye_item, discover_fjdarye_item, parse_fjdarye_item

FJDARYE_POWER_SUPPLY_UNIT = ".1.3.6.1.4.1.211.1.21.1.60"  # fjdarye60

snmp_section_fjdarye_power_supply_units = SNMPSection(
    name="fjdarye_power_supply_units",
    parse_function=parse_fjdarye_item,
    fetch=[SNMPTree(base=f"{FJDARYE_POWER_SUPPLY_UNIT}.2.9.2.1", oids=["1", "3"])],
    detect=equals(".1.3.6.1.2.1.1.2.0", FJDARYE_POWER_SUPPLY_UNIT),
)

check_plugin_fjdarye_power_supply_units = CheckPlugin(
    name="fjdarye_power_supply_units",
    service_name="PSU %s",
    discovery_function=discover_fjdarye_item,
    check_function=check_fjdarye_item,
)
