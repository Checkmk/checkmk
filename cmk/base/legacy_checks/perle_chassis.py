#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.perle import perle_check_alarms
from cmk.base.check_legacy_includes.temperature import check_temperature

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}

# .1.3.6.1.4.1.1966.21.1.1.1.1.1.1.2.1 MCR1900 --> PERLE-MCR-MGT-MIB::chassisModelName.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.1.1.4.1 103-001715T10033 --> PERLE-MCR-MGT-MIB::chassisSerialNumber.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.1.1.5.1 0.0 --> PERLE-MCR-MGT-MIB::chassisBootloaderVersion.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.1.1.6.1 1.0G6 --> PERLE-MCR-MGT-MIB::chassisFirmwareVersion.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.1.1.7.1 0 --> PERLE-MCR-MGT-MIB::chassisOutStandWarnAlarms.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.1.1.8.1 0 --> PERLE-MCR-MGT-MIB::chassisDiagStatus.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.1.1.9.1 23 --> PERLE-MCR-MGT-MIB::chassisTemperature.1


def inventory_perle_chassis(section):
    return [(None, None)]


def check_perle_chassis(_no_item, _no_params, section):
    map_diag_states = {
        "0": (0, "passed"),
        "1": (1, "firmware download required"),
        "2": (2, "temperature sensor not functional"),
    }

    state, state_readable = map_diag_states[section.diagnosis_state]
    yield state, "Diagnostic result: %s" % state_readable
    yield perle_check_alarms(section.alarms)


check_info["perle_chassis"] = LegacyCheckDefinition(
    name="perle_chassis",
    service_name="Chassis status",
    discovery_function=inventory_perle_chassis,
    check_function=check_perle_chassis,
)


def inventory_perle_chassis_temp(info):
    return [("chassis", {})]


def check_perle_chassis_temp(item, params, section):
    return check_temperature(section.temp, params, "perle_chassis_temp")


check_info["perle_chassis.temp"] = LegacyCheckDefinition(
    name="perle_chassis_temp",
    service_name="Temperature %s",
    sections=["perle_chassis"],
    discovery_function=inventory_perle_chassis_temp,
    check_function=check_perle_chassis_temp,
    check_ruleset_name="temperature",
)
