#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.didactum import (
    discover_didactum_sensors,
    parse_didactum_sensors,
)
from cmk.plugins.lib.didactum import DETECT_DIDACTUM

check_info = {}

# .1.3.6.1.4.1.46501.5.1.1.4.101001 dry --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretType.101001
# .1.3.6.1.4.1.46501.5.1.1.4.101002 dry --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretType.101002
# .1.3.6.1.4.1.46501.5.1.1.4.101003 dry --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretType.101003
# .1.3.6.1.4.1.46501.5.1.1.4.101004 dry --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretType.101004
# .1.3.6.1.4.1.46501.5.1.1.5.101001 Dry-1 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretName.101001
# .1.3.6.1.4.1.46501.5.1.1.5.101002 Dry-2 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretName.101002
# .1.3.6.1.4.1.46501.5.1.1.5.101003 Dry-3 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretName.101003
# .1.3.6.1.4.1.46501.5.1.1.5.101004 Dry-4 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretName.101004
# .1.3.6.1.4.1.46501.5.1.1.6.101001 normal --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretState.101001
# .1.3.6.1.4.1.46501.5.1.1.6.101002 normal --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretState.101002
# .1.3.6.1.4.1.46501.5.1.1.6.101003 normal --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretState.101003
# .1.3.6.1.4.1.46501.5.1.1.6.101004 normal --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretState.101004
# .1.3.6.1.4.1.46501.5.1.1.7.101001 0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretValue.101001
# .1.3.6.1.4.1.46501.5.1.1.7.101002 0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretValue.101002
# .1.3.6.1.4.1.46501.5.1.1.7.101003 0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretValue.101003
# .1.3.6.1.4.1.46501.5.1.1.7.101004 0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsDiscretValue.101004


def inventory_didactum_sensors_discrete_dry(parsed):
    yield from discover_didactum_sensors(parsed, "dry")
    yield from discover_didactum_sensors(parsed, "smoke")


def check_didactum_sensors_discrete_dry(item, params, parsed):
    if item in parsed.get("dry", {}):
        data = parsed["dry"][item]
    elif item in parsed.get("smoke", {}):
        data = parsed["smoke"][item]
    else:
        return 3, "Discrete sensor %s not found in SNMP data." % item
    return data["state"], "Status: %s" % data["state_readable"]


check_info["didactum_sensors_discrete"] = LegacyCheckDefinition(
    name="didactum_sensors_discrete",
    detect=DETECT_DIDACTUM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.46501.5.1.1",
        oids=["4", "5", "6"],
    ),
    parse_function=parse_didactum_sensors,
    service_name="Discrete sensor %s",
    discovery_function=inventory_didactum_sensors_discrete_dry,
    check_function=check_didactum_sensors_discrete_dry,
)
