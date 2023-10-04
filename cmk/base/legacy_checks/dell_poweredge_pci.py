#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.dell_poweredge import (
    check_dell_poweredge_pci,
    inventory_dell_poweredge_pci,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.dell import DETECT_IDRAC_POWEREDGE

check_info["dell_poweredge_pci"] = LegacyCheckDefinition(
    detect=DETECT_IDRAC_POWEREDGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5.4.1100.80.1",
        oids=["5", "7", "8", "9", "12"],
    ),
    service_name="PCI %s",
    discovery_function=inventory_dell_poweredge_pci,
    check_function=check_dell_poweredge_pci,
)
