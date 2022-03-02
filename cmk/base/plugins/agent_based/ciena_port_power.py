# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from math import log10
from typing import Mapping, NamedTuple

from .agent_based_api.v1 import check_levels, OIDEnd, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.ciena_ces import DETECT_CIENA_5142, DETECT_CIENA_5171

inf = float("inf")


class PowerReading(NamedTuple):
    power: float
    treshold_upper: float
    treshold_lower: float


class PortPower(NamedTuple):
    receive: PowerReading
    transmit: PowerReading


Section = Mapping[str, PortPower]


def _micro_watt_to_dBm(m_w: int) -> float:
    # values where m_w = 0 are handled later
    if m_w == 0:
        return -inf
    return 10 * log10(m_w / 1000)


def parse_ciena_port_power(string_table: StringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> string_table = [['1', '4', '631', '5', '282', '794', '100'],
    ... ['2', '736', '1258', '25', '537', '1778', '199'],
    ... ['3', '0', '1258', '25', '0', '1778', '199']]
    >>> pprint(parse_ciena_port_power(string_table))
    {'1': PortPower(receive=PowerReading(power=-23.979400086720375, treshold_upper=-1.9997064075586568, treshold_lower=-23.010299956639813), transmit=PowerReading(power=-5.49750891680639, treshold_upper=-1.0017949757290372, treshold_lower=-10.0)),
     '2': PortPower(receive=PowerReading(power=-1.3312218566250114, treshold_upper=0.9968064110925012, treshold_lower=-16.02059991327962), transmit=PowerReading(power=-2.7002571430044435, treshold_upper=2.4993175663419493, treshold_lower=-7.011469235902933)),
     '3': PortPower(receive=PowerReading(power=-inf, treshold_upper=0.9968064110925012, treshold_lower=-16.02059991327962), transmit=PowerReading(power=-inf, treshold_upper=2.4993175663419493, treshold_lower=-7.011469235902933))}
    """
    return {
        oid_end: PortPower(
            PowerReading(*map(_micro_watt_to_dBm, map(int, row[0:3]))),
            PowerReading(*map(_micro_watt_to_dBm, map(int, row[3:]))),
        )
        for oid_end, *row in string_table
    }


def discover_ciena_port_power(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_ciena_port_power(item: str, section: Section) -> CheckResult:
    if item not in section:
        return
    port_power = section[item]
    received_power = port_power.receive
    transmitted_power = port_power.transmit

    def render_func(x: float) -> str:
        return "%.3f dBm" % x

    # Currently, the switch sometimes reports 0 micro_watt. For the most part it does this, if the
    # port does not support transmition. If we convert this to dBm, it breaks our metric.
    if received_power.power != -inf:
        yield from check_levels(
            value=received_power.power,
            metric_name="input_signal_power_dbm",
            levels_upper=(received_power.treshold_upper, received_power.treshold_upper),
            levels_lower=(received_power.treshold_lower, received_power.treshold_lower),
            render_func=render_func,
            label="Receive",
        )
        yield Result(
            state=State.OK,
            notice=f"Receive: crit above {received_power.treshold_upper}, "
            f"crit below {received_power.treshold_lower}",
        )
    else:
        yield Result(state=State.OK, summary="Received signal power is 0 watt")
    if transmitted_power.power != -inf:
        yield from check_levels(
            value=transmitted_power.power,
            metric_name="output_signal_power_dbm",
            levels_upper=(transmitted_power.treshold_upper, transmitted_power.treshold_upper),
            levels_lower=(transmitted_power.treshold_lower, transmitted_power.treshold_lower),
            render_func=render_func,
            label="Transmit",
        )
        yield Result(
            state=State.OK,
            notice=f"Transmit: crit above {transmitted_power.treshold_upper}, "
            f"crit below {transmitted_power.treshold_lower}",
        )
    else:
        yield Result(state=State.OK, summary="Transmitted signal power is 0 watt")


register.check_plugin(
    name="ciena_port_power",
    sections=["ciena_port_power"],
    service_name="Port %s XCVR Power",
    discovery_function=discover_ciena_port_power,
    check_function=check_ciena_port_power,
)

register.snmp_section(
    name="ciena_port_power_5142",
    parsed_section_name="ciena_port_power",
    parse_function=parse_ciena_port_power,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6141.2.60.4.1.1.1.1",
        oids=[
            OIDEnd(),
            "19",  # wwpLeosPortXcvrRxPower
            "42",  # wwpLeosPortXcvrHighRxPwAlarmThreshold
            "43",  # wwpLeosPortXcvrLowRxPwAlarmThreshold
            "27",  # wwpLeosPortXcvrTxOutputPw
            "40",  # wwpLeosPortXcvrHighTxPwAlarmThreshold
            "41",  # wwpLeosPortXcvrLowTxPwAlarmThreshold
        ],
    ),
    detect=DETECT_CIENA_5142,
)
register.snmp_section(
    name="ciena_port_power_5171",
    parsed_section_name="ciena_port_power",
    parse_function=parse_ciena_port_power,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1271.2.1.9.1.1.1.1",
        oids=[
            OIDEnd(),
            "6",  # cienaCesPortXcvrRxPowerx
            "15",  # cienaCesPortXcvrHighRxPwAlarmThreshold
            "16",  # cienaCesPortXcvrLowRxPwAlarmThreshold
            "35",  # cienaCesPortXcvrTxOutputPower
            "13",  # cienaCesPortXcvrHighTxPwAlarmThreshold
            "14",  # cienaCesPortXcvrLowTxPwAlarmThreshold
        ],
    ),
    detect=DETECT_CIENA_5171,
)
