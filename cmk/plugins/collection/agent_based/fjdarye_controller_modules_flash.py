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


from cmk.agent_based.v2 import CheckPlugin, SNMPSection, SNMPTree
from cmk.plugins.lib.fjdarye import (
    check_fjdarye_item,
    DETECT_FJDARYE,
    discover_fjdarye_item,
    FJDARYE_SUPPORTED_DEVICES,
    parse_fjdarye_item,
)

snmp_section_fjdarye_controller_modules_flash = SNMPSection(
    name="fjdarye_controller_modules_flash",
    parse_function=parse_fjdarye_item,
    fetch=[
        SNMPTree(base=f"{device_oid}.2.4.2.1", oids=["1", "3"])
        for device_oid in FJDARYE_SUPPORTED_DEVICES
    ],
    detect=DETECT_FJDARYE,
)


check_plugin_fjdarye_controller_modules_flash = CheckPlugin(
    name="fjdarye_controller_modules_flash",
    service_name="Controller Module Flash %s",
    discovery_function=discover_fjdarye_item,
    check_function=check_fjdarye_item,
)
