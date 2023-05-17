#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import any_of, LegacyCheckDefinition, startswith
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree

# Knowledge from customer:
# Devices with OID_END=38 are 12 port power switches with two powerbanks.
# Means each powerbank has 6 outlets. Here we can use ChanStatus in order
# to find out if one powerbank is enabled/used.
#
# Device with OID_END=19 is a simple switch outlet: 1 Port and 1 powerbank
# Once it's plugged in, the state is "on". Thus we use PortState in
# discovering function.

factory_settings["gude_powerbank_default_levels"] = {
    "voltage": (220, 210),
    "current": (15, 16),
}


def parse_gude_powerbanks(info):
    map_port_states = {
        "0": (2, "off"),
        "1": (0, "on"),
    }
    map_channel_states = {
        "0": (2, "data not active"),
        "1": (0, "data valid"),
    }

    ports = dict(info[0])

    parsed = {}
    for oid, block in zip(_TABLES, info[2:]):
        for (
            idx,
            dev_state,
            energy_str,
            active_power_str,
            current_str,
            volt_str,
            freq_str,
            appower_str,
        ) in block:
            device_state = (
                map_port_states[ports[idx]] if oid == 19 else map_channel_states[dev_state]
            )

            parsed.setdefault(idx, {"device_state": device_state})

            for what, key, factor in [
                (energy_str, "energy", 1.0),
                (active_power_str, "power", 1.0),
                (current_str, "current", 0.001),
                (volt_str, "voltage", 1.0),
                (freq_str, "frequency", 0.01),
                (appower_str, "appower", 1.0),
            ]:
                parsed[idx][key] = float(what) * factor

    return parsed


def inventory_gude_powerbanks(parsed):
    return [
        (powerbank, {})
        for powerbank, attrs in parsed.items()
        if attrs["device_state"][1] not in ["off", "data not active"]
    ]


_TABLES = (19, 38)

check_info["gude_powerbanks"] = LegacyCheckDefinition(
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.19"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.38"),
    ),
    parse_function=parse_gude_powerbanks,
    discovery_function=inventory_gude_powerbanks,
    check_function=check_elphase,
    service_name="Powerbank %s",
    fetch=[
        SNMPTree(
            base=f".1.3.6.1.4.1.28507.{table}.1.3.1.2.1",
            oids=[OIDEnd(), "3"],
        )
        for table in _TABLES
    ]
    + [
        SNMPTree(
            base=f".1.3.6.1.4.1.28507.{table}.1.5.1.2.1",
            oids=[OIDEnd(), "2", "3", "4", "5", "6", "7", "10"],
        )
        for table in _TABLES
    ],
    default_levels_variable="gude_powerbank_default_levels",
    check_ruleset_name="el_inphase",
    check_default_parameters={
        "voltage": (220, 210),
        "current": (15, 16),
    },
)
