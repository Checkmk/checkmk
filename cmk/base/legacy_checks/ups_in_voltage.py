#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, LegacyCheckDefinition
from cmk.base.check_legacy_includes.ups_in_voltage import check_ups_in_voltage
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.utils.ups import DETECT_UPS_GENERIC

ups_in_voltage_default_levels = (210, 180)  # warning / critical


@discover(default_params="ups_in_voltage_default_levels")
def inventory_ups_in_voltage(entry):
    return entry[0] if int(entry[1]) > 0 else False


check_info["ups_in_voltage"] = LegacyCheckDefinition(
    detect=DETECT_UPS_GENERIC,
    discovery_function=inventory_ups_in_voltage,
    check_function=check_ups_in_voltage,
    service_name="IN voltage phase %s",
    check_ruleset_name="evolt",
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.33.1.3.3.1",
        oids=[OIDEnd(), "3"],
    ),
)
