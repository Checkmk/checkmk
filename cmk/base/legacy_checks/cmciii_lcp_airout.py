#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cmciii import (
    check_cmciii_lcp_fanunit,
    inventory_cmciii_lcp_fanunit,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.plugins.lib.cmciii import DETECT_CMCIII_LCP

# Note: this check is obsolete, please use cmciii.temp_in_out instead


check_info["cmciii_lcp_airout"] = LegacyCheckDefinition(
    detect=DETECT_CMCIII_LCP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2606.7.4.2.2.1.10.2",
        oids=["6", "13", "25", "32", "30", "29", "28", "27", "26", "10", "11", "12"],
    ),
    service_name="Temperature %s",
    discovery_function=lambda info: inventory_cmciii_lcp_fanunit("Air", "Out", info),
    check_function=check_cmciii_lcp_fanunit,
    check_ruleset_name="temperature",
)
