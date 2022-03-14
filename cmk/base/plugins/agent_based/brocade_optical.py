#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, TypedDict, Union

from .agent_based_api.v1 import (
    get_value_store,
    Metric,
    OIDEnd,
    register,
    Result,
    Service,
    SNMPTree,
    startswith,
)
from .agent_based_api.v1 import State as state
from .agent_based_api.v1 import type_defs
from .utils import interfaces, temperature

# .1.3.6.1.4.1.1991.1.1.3.3.6.1.1.1  41.4960 C: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.6.1.1.2  50.9531 C: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.6.1.1.65  49.8007 C: Normal
#
# .1.3.6.1.4.1.1991.1.1.3.3.6.1.2.1 007.9643 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.6.1.2.2 007.5898 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.6.1.2.65 006.9644 dBm: Normal
#
# .1.3.6.1.4.1.1991.1.1.3.3.6.1.3.1 000.6744 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.6.1.3.2 -023.0102 dBm: Low-Alarm
# .1.3.6.1.4.1.1991.1.1.3.3.6.1.3.65 -015.6863 dBm: Low-Alarm
#
#
# .1.3.6.1.4.1.1991.1.1.3.3.9.1.1.1 100GBASE-LR4 CFP2
# .1.3.6.1.4.1.1991.1.1.3.3.9.1.1.2 100GBASE-LR4 CFP2
# .1.3.6.1.4.1.1991.1.1.3.3.9.1.1.65 100GBASE-LR4 CFP2
#
# .1.3.6.1.4.1.1991.1.1.3.3.9.1.4.1 12-1234567-01
# .1.3.6.1.4.1.1991.1.1.3.3.9.1.4.2 12-1234567-01
# .1.3.6.1.4.1.1991.1.1.3.3.9.1.4.65 12-1234567-01
#
# .1.3.6.1.4.1.1991.1.1.3.3.9.1.5.1 XXX00000X00X00X
# .1.3.6.1.4.1.1991.1.1.3.3.9.1.5.2 XXX000000000XX0
# .1.3.6.1.4.1.1991.1.1.3.3.9.1.5.65 XXX0000000000X
#
#
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.2.1.1    41.5000 C: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.2.1.2    41.4960 C: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.2.1.3    41.4921 C: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.2.1.4    41.5039 C: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.2.2.1    50.9687 C: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.2.2.2    50.9843 C: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.2.2.3    50.9570 C: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.2.2.4    50.9570 C: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.2.65.1    49.7539 C: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.2.65.2    49.7734 C: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.2.65.3    49.7578 C: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.2.65.4    49.7851 C: Normal
#
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.3.1.1   001.9072 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.3.1.2   002.5098 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.3.1.3   001.3392 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.3.1.4   001.9473 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.3.2.1   001.5615 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.3.2.2   001.4924 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.3.2.3   001.6840 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.3.2.4   001.5421 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.3.65.1   000.0543 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.3.65.2   000.6069 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.3.65.3   001.6307 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.3.65.4   001.3152 dBm: Normal
#
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.4.1.1  -004.9935 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.4.1.2  -005.4030 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.4.1.3  -005.3017 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.4.1.4  -005.6479 dBm: Normal
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.4.2.1  -026.0205 dBm: Low-Alarm
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.4.2.2  -214.3647 dBm: Low-Alarm
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.4.2.3  -214.3647 dBm: Low-Alarm
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.4.2.4  -024.9485 dBm: Low-Alarm
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.4.65.1  -021.4266 dBm: Low-Alarm
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.4.65.2  -020.3621 dBm: Low-Alarm
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.4.65.3  -022.4412 dBm: Low-Alarm
# .1.3.6.1.4.1.1991.1.1.3.3.10.1.4.65.4  -021.8045 dBm: Low-Alarm

OPER_STATUS_MAP = {
    "1": "up",
    "2": "down",
    "3": "testing",
    "4": "unknown",
    "5": "dormant",
    "6": "not present",
    "7": "lower layer down",
    "8": "degraded",
    "9": "admin down",
}

ValueAndStatus = Union[Tuple[float, str], Tuple[None, None]]
Lane = Mapping[str, ValueAndStatus]


class Port(TypedDict, total=False):
    temp: ValueAndStatus
    tx_light: ValueAndStatus
    rx_light: ValueAndStatus
    port_type: str
    description: str
    operational_status: str
    type: str
    part: str
    serial: str
    lanes: Dict[int, Lane]


Section = Dict[str, Port]


def _parse_value(value_string: str) -> ValueAndStatus:
    if value_string == "N/A" or value_string.lower() == "not supported":
        return None, None
    try:
        val, _unit, status = value_string.split()
        return float(val), status
    except ValueError:
        return None, None


def parse_brocade_optical(string_table: List[type_defs.StringTable]) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_brocade_optical([
    ... [['1409', '10GigabitEthernet23/1', '6', '1'],
    ...  ['1410', '10GigabitEthernet23/2', '6', '2'],
    ...  ['1411', '10GigabitEthernet23/3', '6', '2'],
    ...  ['2049', 'EthernetManagement1', '6', '1'], ['33554433', 'lb1', '24', '1'],
    ...  ['67108864', 'tnl0', '150', '1'], ['67108865', 'tnl1', '150', '1'],
    ...  ['67108866', 'tnl2', '150', '1'], ['67108867', 'tnl3', '150', '1'],
    ...  ['83886085', 'LAG5', '202', '2']],
    ... [['      N/A    ', '-001.6045 dBm: Normal', '-002.2504 dBm: Normal', '1409'],
    ...  ['31.4882 C: Normal', '-001.4508 dBm: Normal', '-036.9897 dBm: Low-Alarm', '1410'],
    ...  ['31.4531 C: Normal', '-001.4194 dBm: Normal', '-033.9794 dBm: Low-Alarm', '1411'],
    ...  [ '29.5703 C: Normal', '-031.5490 dBm: Low-Alarm', '-036.9897 dBm: Low-Alarm', '1412']],
    ... [['10GE LR 10km SFP+', '57-0000076-01', 'ADF2094300014TL', '1409'],
    ...  ['10GE LR 10km SFP+', '57-0000076-01', 'ADF2094300014UN', '1410'],
    ...  ['10GE LR 10km SFP+', '57-0000076-01', 'ADF2094300014UL', '1411']],
    ... [['31.4531 C: Normal', '-001.6045 dBm: Normal', '-002.2504 dBm: Normal', '1409.1']],
    ... ]))
    {'1409': {'description': '10GigabitEthernet23/1',
              'lanes': {1: {'rx_light': (-2.2504, 'Normal'),
                            'temp': (31.4531, 'Normal'),
                            'tx_light': (-1.6045, 'Normal')}},
              'operational_status': '1',
              'part': '57-0000076-01',
              'port_type': '6',
              'rx_light': (-2.2504, 'Normal'),
              'serial': 'ADF2094300014TL',
              'temp': (None, None),
              'tx_light': (-1.6045, 'Normal'),
              'type': '10GE LR 10km SFP+'},
     '1410': {'description': '10GigabitEthernet23/2',
              'operational_status': '2',
              'part': '57-0000076-01',
              'port_type': '6',
              'rx_light': (-36.9897, 'Low-Alarm'),
              'serial': 'ADF2094300014UN',
              'temp': (31.4882, 'Normal'),
              'tx_light': (-1.4508, 'Normal'),
              'type': '10GE LR 10km SFP+'},
     '1411': {'description': '10GigabitEthernet23/3',
              'operational_status': '2',
              'part': '57-0000076-01',
              'port_type': '6',
              'rx_light': (-33.9794, 'Low-Alarm'),
              'serial': 'ADF2094300014UL',
              'temp': (31.4531, 'Normal'),
              'tx_light': (-1.4194, 'Normal'),
              'type': '10GE LR 10km SFP+'},
     '1412': {'rx_light': (-36.9897, 'Low-Alarm'),
              'temp': (29.5703, 'Normal'),
              'tx_light': (-31.549, 'Low-Alarm')}}
    """

    if_info, if_data, if_ids, lanes = string_table
    parsed: Section = {}

    for temp, tx_light, rx_light, if_id in if_data:
        parsed.setdefault(
            if_id,
            {
                "temp": _parse_value(temp),
                "tx_light": _parse_value(tx_light),
                "rx_light": _parse_value(rx_light),
            },
        )

    for if_id, if_descr, if_type, if_operstatus in if_info:
        if if_id in parsed:
            parsed[if_id].update(
                {"port_type": if_type, "description": if_descr, "operational_status": if_operstatus}
            )

    # add informational values
    for media_type, part, serial, if_id in if_ids:
        if if_id in parsed:
            parsed[if_id].update({"type": media_type, "part": part, "serial": serial})

    # add per-lane data
    for temp, tx_light, rx_light, lane in lanes:
        if_id, lane = lane.split(".")
        if if_id in parsed:
            parsed[if_id].setdefault("lanes", {}).setdefault(
                int(lane),
                {
                    "temp": _parse_value(temp),
                    "tx_light": _parse_value(tx_light),
                    "rx_light": _parse_value(rx_light),
                },
            )
    return parsed


register.snmp_section(
    name="brocade_optical",
    parse_function=parse_brocade_optical,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.2.2.1",
            oids=[
                "1",  # ifIndex
                "2",  # ifDescr
                "3",  # ifType
                "8",  # ifOperStatus
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1991.1.1.3.3.6.1",
            oids=[
                "1",  # temperature
                "2",  # TX light level
                "3",  # RX light level
                OIDEnd(),
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1991.1.1.3.3.9.1",
            oids=[
                "1",  # media type
                "4",  # part number
                "5",  # serial number
                OIDEnd(),
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1991.1.1.3.3.10.1",
            oids=[
                "2",  # lane temperature
                "3",  # lane TX light level
                "4",  # lane RX light level
                OIDEnd(),
            ],
        ),
    ],
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1991.1."),
)


def _check_matching_conditions(
    port: Port,
    matching_conditions: interfaces.MatchingConditions,
) -> bool:
    port_types = matching_conditions.get("porttypes")
    port_states = matching_conditions.get("portstates")
    return (
        (port_types is None or port["port_type"] in port_types)
        and (port_states is None or port["operational_status"] in port_states)
        and interfaces.check_regex_match_conditions(
            port["description"],
            matching_conditions.get("match_desc"),
        )
    )


def discover_brocade_optical(
    params: Sequence[Mapping[str, Any]],
    section: Section,
) -> type_defs.DiscoveryResult:
    if section:
        pad_width = max(map(len, section))
    else:
        pad_width = 0

    for key, entry in section.items():
        # find the most specific rule which applies to this interface and which has single-interface
        # discovery settings
        for rule in params:
            if "discovery_single" in rule and _check_matching_conditions(
                entry,
                rule["matching_conditions"][1],
            ):
                if rule["discovery_single"][0]:
                    # if pad_width == 0 then "0" * -X == ""
                    yield Service(item="0" * (pad_width - len(key)) + key)
                break


def _monitoring_state(
    reading: ValueAndStatus,
    temp_alert: bool,
) -> int:
    if reading[0] is None:
        return 3
    if temp_alert:
        status = reading[1].lower()
        if status == "normal":
            return 0
        if status.endswith("warn"):
            return 1
        return 2
    return 0


def _infotext(
    reading: ValueAndStatus,
    title: str,
    unit: str,
) -> str:
    assert reading[0] is not None
    if reading[0] < -214748.0:
        reading_text = "off"
    else:
        reading_text = "%.1f %s" % (reading[0], unit)
    return "%s %s (%s)" % (title, reading_text, reading[1])


def _check_light(
    reading: ValueAndStatus,
    metric_name: str,
    params: Mapping[str, Any],
    lane_num: Optional[int] = None,
) -> type_defs.CheckResult:
    if any(x is None for x in reading):
        return
    txt = _infotext(
        reading,
        "%s Light%s"
        % (
            metric_name.split("_")[0].upper(),
            lane_num is not None and " (Lane %d)" % lane_num or "",
        ),
        "dBm",
    )
    mon_state = state(_monitoring_state(reading, params.get(metric_name, False)))
    if lane_num is None:
        yield Result(
            state=mon_state,
            summary=txt,
        )
    else:
        yield Result(
            state=mon_state,
            notice=txt,
        )
    yield Metric(
        metric_name + (lane_num is not None and "_%d" % lane_num or ""),
        reading[0],  # type: ignore[arg-type]
    )


def check_brocade_optical(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> type_defs.CheckResult:
    item = item.lstrip("0")
    if item not in section:
        return
    iface = section[item]

    add_info = []
    if "serial" in iface:
        add_info.append("S/N %s" % iface["serial"])
    if "part" in iface:
        add_info.append("P/N %s" % iface["part"])

    oper_status = iface["operational_status"]
    oper_status_readable = OPER_STATUS_MAP.get(oper_status, "unknown[%s]" % oper_status)
    if add_info:
        yield Result(
            state=state.OK,
            summary="[%s] Operational %s" % (", ".join(add_info), oper_status_readable),
        )
    else:
        yield Result(
            state=state.OK,
            summary="Operational %s" % oper_status_readable,
        )

    try:
        temp = iface["temp"][0]
    except KeyError:
        temp = None
    if temp is not None:
        yield from temperature.check_temperature(
            temp,
            None,
            unique_name="brocade_optical_%s" % item,
            value_store=get_value_store(),
            dev_status=_monitoring_state(iface["temp"], params.get("temp", False)),
        )
    yield from _check_light(
        iface["tx_light"],
        "tx_light",
        params,
    )
    yield from _check_light(
        iface["rx_light"],
        "rx_light",
        params,
    )

    if "lanes" in iface and params.get("lanes"):
        for num, lane in iface["lanes"].items():
            temp = lane["temp"][0]
            assert temp is not None
            lane_temp_output = list(
                temperature.check_temperature(
                    temp,
                    None,
                    unique_name="brocade_optical_lane%d_%s" % (num, item),
                    value_store=get_value_store(),
                    dev_status=_monitoring_state(lane["temp"], params.get("temp", False)),
                )
            )
            lane_temp_result = [res for res in lane_temp_output if isinstance(res, Result)][0]
            lane_temp_metric = [res for res in lane_temp_output if isinstance(res, Metric)][0]
            yield Result(
                state=lane_temp_result.state,
                notice="Temperature (Lane %d) %s" % (num, lane_temp_result.summary),
            )
            yield Metric(
                "port_%s_%d" % (lane_temp_metric.name, num),
                lane_temp_metric.value,
            )

            yield from _check_light(
                lane["tx_light"],
                "tx_light",
                params,
                lane_num=num,
            )
            yield from _check_light(
                lane["rx_light"],
                "rx_light",
                params,
                lane_num=num,
            )


register.check_plugin(
    name="brocade_optical",
    service_name="Interface %s Optical",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_brocade_optical,
    check_ruleset_name="brocade_optical",
    check_default_parameters={},
    check_function=check_brocade_optical,
)
