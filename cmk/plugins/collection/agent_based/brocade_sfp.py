#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    OIDCached,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.brocade import (
    brocade_fcport_getitem,
    brocade_fcport_inventory_this_port,
    DETECT,
    DISCOVERY_DEFAULT_PARAMETERS,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict


class Port(TypedDict):
    port_name: str
    temp: int
    phystate: int
    opstate: int
    admstate: int
    voltage: float
    current: float
    rx_power: float
    tx_power: float
    is_isl: bool


Section = Mapping[int, Port]


def parse_brocade_sfp(string_table: Sequence[StringTable]) -> Section:
    parsed: dict[int, Port] = {}

    isl_ports = [int(x[0]) for x in string_table[1]]

    for fcport_info, values in zip(string_table[0], string_table[2]):
        # Observed in the wild: Either all of the values are present
        # or none of them.
        if values[0] == "NA":
            continue

        port_index = int(fcport_info[0])

        parsed[port_index] = {
            "port_name": fcport_info[4],
            "temp": int(values[0]),  # °C
            "phystate": int(fcport_info[1]),
            "opstate": int(fcport_info[2]),
            "admstate": int(fcport_info[3]),
            "voltage": float(values[1]) / 1000,  # mV -> V
            "current": float(values[2]) / 1000,  # mA -> A
            "rx_power": float(values[3]),  # dBm
            "tx_power": float(values[4]),  # dBm
            "is_isl": bool(port_index in isl_ports),
        }

    return parsed


snmp_section_brocade_sfp = SNMPSection(
    name="brocade_sfp",
    parse_function=parse_brocade_sfp,
    detect=DETECT,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.1588.2.1.1.1.6.2.1",
            oids=[
                OIDCached("1"),  # swFCPortIndex
                OIDCached("3"),  # swFCPortPhyState
                OIDCached("4"),  # swFCPortOpStatus
                OIDCached("5"),  # swFCPortAdmStatus
                OIDCached("36"),  # swFCPortName  (not supported by all devices)
            ],
        ),
        # Information about Inter-Switch-Links (contains baud rate of port)
        SNMPTree(
            base=".1.3.6.1.4.1.1588.2.1.1.1.2.9.1",
            oids=[
                OIDCached("2"),  # swNbMyPort
            ],
        ),
        # NOTE: It appears that the port name and index in connUnitPortEntry
        #       are identical to the ones in the table used by
        #       brocade_fcport. We work on this assumption for the time being,
        #       meaning we use the same table as in brocade_fcport (see above)
        #       which we need anyway for PhyState, OpStatus and AdmStatus.
        #       Please check the connUnitPortEntry table (.1.3.6.1.3.94.1.10.1)
        #       should you come across a device for which this assumption
        #       does not hold.
        SNMPTree(
            base=".1.3.6.1.4.1.1588.2.1.1.1.28.1.1",
            oids=[  # FA-EXT-MIB::swSfpStatEntry
                # AUGMENTS {connUnitPortEntry}
                "1",  # swSfpTemperature
                "2",  # swSfpVoltage
                "3",  # swSfpCurrent
                "4",  # swSfpRxPower
                "5",  # swSfpTxPower
            ],
        ),
    ],
)


def discover_brocade_sfp(params: Mapping[str, Any], section: Section) -> DiscoveryResult:
    number_of_ports = len(section)
    for port_index, port_info in section.items():
        if brocade_fcport_inventory_this_port(
            admstate=port_info["admstate"],
            phystate=port_info["phystate"],
            opstate=port_info["opstate"],
            settings=params,
        ):
            yield Service(
                item=brocade_fcport_getitem(
                    number_of_ports=number_of_ports,
                    index=port_index,
                    portname=port_info["port_name"],
                    is_isl=port_info["is_isl"],
                    settings=params,
                )
            )


#   .--Temperature---------------------------------------------------------.
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def check_brocade_sfp_temp(item: str, params: TempParamDict, section: Section) -> CheckResult:
    # TODO: Move this magical plucking apart of the
    #       item to brocade.include and do the same
    #       for brocade.fcport.
    port_index = int(item.split()[0]) + 1
    if port_index not in section:
        return
    port_info = section[port_index]

    yield from check_temperature(
        port_info["temp"], params, unique_name=item, value_store=get_value_store()
    )


check_plugin_brocade_sfp_temp = CheckPlugin(
    name="brocade_sfp_temp",
    service_name="SFP Temperature %s",
    sections=["brocade_sfp"],
    discovery_function=discover_brocade_sfp,
    discovery_ruleset_name="brocade_fcport_inventory",
    discovery_default_parameters=DISCOVERY_DEFAULT_PARAMETERS,
    check_function=check_brocade_sfp_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)

# .
#   .--Power level - Main check--------------------------------------------.
#   |          ____                          _                _            |
#   |         |  _ \ _____      _____ _ __  | | _____   _____| |           |
#   |         | |_) / _ \ \ /\ / / _ \ '__| | |/ _ \ \ / / _ \ |           |
#   |         |  __/ (_) \ V  V /  __/ |    | |  __/\ V /  __/ |           |
#   |         |_|   \___/ \_/\_/ \___|_|    |_|\___| \_/ \___|_|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Also includes information about current and voltage                  |
#   '----------------------------------------------------------------------'


def check_brocade_sfp(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    # TODO: Move this magical plucking apart of the
    #       item to brocade.include and do the same
    #       for brocade.fcport.
    port_index = int(item.split()[0]) + 1
    if port_index not in section:
        return
    port_info = section[port_index]

    # levels are given in an uncommon order at the rulespec
    # We have crit_lower, warn_lower, warn_upper, crit_upper
    # but we need warn_upper, warn_upper, warn_lower, crit_lower
    def _levels_lower(key: str) -> tuple[float, float] | None:
        return (v[1], v[0]) if (v := params.get(key)) else None

    def _levels_upper(key: str) -> tuple[float, float] | None:
        return (v[2], v[3]) if (v := params.get(key)) else None

    yield from check_levels_v1(
        port_info["rx_power"],
        metric_name="input_signal_power_dbm",
        levels_lower=_levels_lower("rx_power"),
        levels_upper=_levels_upper("rx_power"),
        render_func=lambda f: "%.2f dBm" % f,
        label="Rx",
    )
    yield from check_levels_v1(
        port_info["tx_power"],
        metric_name="output_signal_power_dbm",
        levels_lower=_levels_lower("tx_power"),
        levels_upper=_levels_upper("tx_power"),
        render_func=lambda f: "%.2f dBm" % f,
        label="Tx",
    )
    yield from check_levels_v1(
        port_info["current"],
        metric_name="current",
        levels_lower=_levels_lower("current"),
        levels_upper=_levels_upper("current"),
        render_func=lambda f: "%.2f A" % f,
        label="Current",
    )
    yield from check_levels_v1(
        port_info["voltage"],
        metric_name="voltage",
        levels_lower=_levels_lower("voltage"),
        levels_upper=_levels_upper("voltage"),
        render_func=lambda f: "%.2f V" % f,
        label="Voltage",
    )


check_plugin_brocade_sfp = CheckPlugin(
    name="brocade_sfp",
    service_name="SFP %s",
    discovery_function=discover_brocade_sfp,
    discovery_ruleset_name="brocade_fcport_inventory",
    discovery_default_parameters=DISCOVERY_DEFAULT_PARAMETERS,
    check_function=check_brocade_sfp,
    check_ruleset_name="brocade_sfp",
    check_default_parameters={},
)
