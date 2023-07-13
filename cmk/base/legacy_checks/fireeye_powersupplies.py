#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.fireeye import check_fireeye_states, inventory_fireeye_generic
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.fireeye import DETECT

# .1.3.6.1.4.1.25597.11.3.1.1.0 Good --> FE-FIREEYE-MIB::fePowerSupplyOverallStatus.0
# .1.3.6.1.4.1.25597.11.3.1.2.0 1 --> FE-FIREEYE-MIB::fePowerSupplyOverallIsHealthy.0


def check_fireeye_powersupplies(_no_item, _no_params, info):
    status, health = info[0]
    for text, (state, state_readable) in check_fireeye_states(
        [(status, "Status"), (health, "Health")]
    ).items():
        yield state, "%s: %s" % (text, state_readable)


check_info["fireeye_powersupplies"] = LegacyCheckDefinition(
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.3.1",
        oids=["1", "2"],
    ),
    service_name="Power supplies summary",
    discovery_function=lambda info: inventory_fireeye_generic(info, False),
    check_function=check_fireeye_powersupplies,
)
