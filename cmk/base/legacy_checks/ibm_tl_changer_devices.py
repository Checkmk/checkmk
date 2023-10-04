#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.ibm_tape_library import ibm_tape_library_get_device_state
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith

# .1.3.6.1.4.1.14851.3.1.11.2.1.4.1 Logical_Library: 1 --> SNIA-SML-MIB::changerDevice-ElementName.1
# .1.3.6.1.4.1.14851.3.1.11.2.1.4.2 Logical_Library: LTO6 --> SNIA-SML-MIB::changerDevice-ElementName.2
# .1.3.6.1.4.1.14851.3.1.11.2.1.8.1 3 --> SNIA-SML-MIB::changerDevice-Availability.1
# .1.3.6.1.4.1.14851.3.1.11.2.1.8.2 3 --> SNIA-SML-MIB::changerDevice-Availability.2
# .1.3.6.1.4.1.14851.3.1.11.2.1.9.1 2 --> SNIA-SML-MIB::changerDevice-OperationalStatus.1
# .1.3.6.1.4.1.14851.3.1.11.2.1.9.2 2 --> SNIA-SML-MIB::changerDevice-OperationalStatus.2


def inventory_ibm_tl_changer_devices(info):
    return [(name.replace("Logical_Library:", "").strip(), None) for name, _avail, _status in info]


def check_ibm_tl_changer_devices(item, params, info):
    for name, avail, status in info:
        if item == name.replace("Logical_Library:", "").strip():
            return ibm_tape_library_get_device_state(avail, status)
    return None


check_info["ibm_tl_changer_devices"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.32925.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14851.3.1.11.2.1",
        oids=["4", "8", "9"],
    ),
    service_name="Changer device %s",
    discovery_function=inventory_ibm_tl_changer_devices,
    check_function=check_ibm_tl_changer_devices,
)
