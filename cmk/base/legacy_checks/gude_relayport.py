#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_legacy_includes.elphase import check_elphase

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith

check_info = {}

# .1.3.6.1.4.1.28507.38.1.3.1.2.1.2.1 TWTA 2 --> GUDEADS-EPC822X-MIB::epc822XPortName.1
# .1.3.6.1.4.1.28507.38.1.3.1.2.1.3.1 0 --> GUDEADS-EPC822X-MIB::epc822XPortState.1
# .1.3.6.1.4.1.28507.38.1.5.1.2.1.4.1 0 --> GUDEADS-EPC822X-MIB::epc822XPowerActive.1
# .1.3.6.1.4.1.28507.38.1.5.1.2.1.5.1 0 --> GUDEADS-EPC822X-MIB::epc822XCurrent.1
# .1.3.6.1.4.1.28507.38.1.5.1.2.1.6.1 228 --> GUDEADS-EPC822X-MIB::epc822XVoltage.1
# .1.3.6.1.4.1.28507.38.1.5.1.2.1.7.1 4995 --> GUDEADS-EPC822X-MIB::epc822XFrequency.1
# .1.3.6.1.4.1.28507.38.1.5.1.2.1.10.1 0 --> GUDEADS-EPC822X-MIB::epc822XPowerApparent.1


def parse_gude_relayport(string_table):
    parsed = {}
    for (
        portname,
        portstate,
        active_power_str,
        current_str,
        volt_str,
        freq_str,
        appower_str,
    ) in string_table:
        parsed.setdefault(
            portname,
            {
                "device_state": {"0": (2, "off"), "1": (0, "on")}[portstate],
            },
        )

        for what, key, factor in [
            (active_power_str, "power", 1.0),
            (current_str, "current", 0.001),
            (volt_str, "voltage", 1.0),
            (freq_str, "frequency", 0.01),
            (appower_str, "appower", 1.0),
        ]:
            parsed[portname][key] = float(what) * factor

    return parsed


def discover_gude_relayport(section):
    yield from ((item, {}) for item in section)


check_info["gude_relayport"] = LegacyCheckDefinition(
    name="gude_relayport",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.38"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.28507.38.1",
        oids=[
            "3.1.2.1.2",
            "3.1.2.1.3",
            "5.5.2.1.4",
            "5.5.2.1.5",
            "5.5.2.1.6",
            "5.5.2.1.7",
            "5.5.2.1.10",
        ],
    ),
    parse_function=parse_gude_relayport,
    service_name="Relay port %s",
    discovery_function=discover_gude_relayport,
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
    check_default_parameters={
        "voltage": (220, 210),
        "current": (15, 16),
    },
)
