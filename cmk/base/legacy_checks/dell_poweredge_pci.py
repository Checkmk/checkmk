#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.dell_poweredge import check_dell_poweredge_pci
from cmk.plugins.dell.lib import DETECT_IDRAC_POWEREDGE

check_info = {}


def discover_dell_poweredge_pci(info):
    inventory = []
    for line in info:
        fqdd = line[4]
        if fqdd != "":
            inventory.append((fqdd, None))
    return inventory


def parse_dell_poweredge_pci(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_poweredge_pci"] = LegacyCheckDefinition(
    name="dell_poweredge_pci",
    parse_function=parse_dell_poweredge_pci,
    detect=DETECT_IDRAC_POWEREDGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5.4.1100.80.1",
        oids=["5", "7", "8", "9", "12"],
    ),
    service_name="PCI %s",
    discovery_function=discover_dell_poweredge_pci,
    check_function=check_dell_poweredge_pci,
)
