#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .agent_based_api.v1 import get_value_store, IgnoreResultsError, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import diskstat, interfaces

# Example output:
# <<<esx_vsphere_counters:sep(124)>>>
# net.broadcastRx|vmnic0|11|number
# net.broadcastRx||11|number
# net.broadcastTx|vmnic0|0|number
# net.broadcastTx||0|number
# net.bytesRx|vmnic0|3820|kiloBytesPerSecond
# net.bytesRx|vmnic1|0|kiloBytesPerSecond
# net.bytesRx|vmnic2|0|kiloBytesPerSecond
# net.bytesRx|vmnic3|0|kiloBytesPerSecond
# net.bytesRx||3820|kiloBytesPerSecond
# net.bytesTx|vmnic0|97|kiloBytesPerSecond
# net.bytesTx|vmnic1|0|kiloBytesPerSecond
# net.bytesTx|vmnic2|0|kiloBytesPerSecond
# net.bytesTx|vmnic3|0|kiloBytesPerSecond
# net.bytesTx||97|kiloBytesPerSecond
# net.droppedRx|vmnic0|0|number
# net.droppedRx|vmnic1|0|number
# net.droppedRx|vmnic2|0|number
# net.droppedRx|vmnic3|0|number
# net.droppedRx||0|number
# net.droppedTx|vmnic0|0|number
# net.droppedTx|vmnic1|0|number
# ...
# datastore.read|4c4ece34-3d60f64f-1584-0022194fe902|0#1#2|kiloBytesPerSecond
# datastore.read|4c4ece5b-f1461510-2932-0022194fe902|0#4#5|kiloBytesPerSecond
# datastore.numberReadAveraged|511e4e86-1c009d48-19d2-bc305bf54b07|0#0#0|number
# datastore.numberWriteAveraged|4c4ece34-3d60f64f-1584-0022194fe902|0#0#1|number
# datastore.totalReadLatency|511e4e86-1c009d48-19d2-bc305bf54b07|0#5#5|millisecond
# datastore.totalWriteLatency|4c4ece34-3d60f64f-1584-0022194fe902|0#2#7|millisecond
# ...
# sys.uptime||630664|second

Values = Sequence[str]
SubSectionCounter = Dict[str, List[Tuple[Values, str]]]
Section = Dict[str, SubSectionCounter]


def parse_esx_vsphere_counters(string_table: StringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_esx_vsphere_counters([
    ... ['disk.numberReadAveraged', 'naa.5000cca05688e814', '0#0', 'number'],
    ... ['disk.write',
    ...  'naa.6000eb39f31c58130000000000000015',
    ...  '0#0',
    ...  'kiloBytesPerSecond'],
    ... ['net.bytesRx', 'vmnic0', '1#1', 'kiloBytesPerSecond'],
    ... ['net.droppedRx', 'vmnic1', '0#0', 'number'],
    ... ['net.errorsRx', '', '0#0', 'number'],
    ... ]))
    {'disk.numberReadAveraged': {'naa.5000cca05688e814': [(['0', '0'], 'number')]},
     'disk.write': {'naa.6000eb39f31c58130000000000000015': [(['0', '0'],
                                                              'kiloBytesPerSecond')]},
     'net.bytesRx': {'vmnic0': [(['1', '1'], 'kiloBytesPerSecond')]},
     'net.droppedRx': {'vmnic1': [(['0', '0'], 'number')]},
     'net.errorsRx': {'': [(['0', '0'], 'number')]}}
    """

    parsed: Section = {}
    # The data reported by the ESX system is split into multiple real time samples with
    # a fixed duration of 20 seconds. A check interval of one minute reports 3 samples
    # The esx_vsphere_counters checks need to figure out by themselves how to handle this data
    for counter, instance, multivalues, unit in string_table:
        values = multivalues.split("#")
        parsed.setdefault(counter, {})
        parsed[counter].setdefault(instance, [])
        parsed[counter][instance].append((values, unit))
    return parsed


register.agent_section(
    name="esx_vsphere_counters",
    parse_function=parse_esx_vsphere_counters,
)


def average_parsed_data(values: Values) -> float:
    """
    >>> average_parsed_data(['1', '2'])
    1.5
    >>> average_parsed_data(['1'])
    1.0
    >>> average_parsed_data([])
    0
    """
    return sum(map(int, values)) / len(values) if values else 0


# .
#   .--Interfaces----------------------------------------------------------.
#   |           ___       _             __                                 |
#   |          |_ _|_ __ | |_ ___ _ __ / _| __ _  ___ ___  ___             |
#   |           | || '_ \| __/ _ \ '__| |_ / _` |/ __/ _ \/ __|            |
#   |           | || | | | ||  __/ |  |  _| (_| | (_|  __/\__ \            |
#   |          |___|_| |_|\__\___|_|  |_|  \__,_|\___\___||___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _get_ctr_multiplier(ctr_name: str) -> int:
    """
    >>> _get_ctr_multiplier('bytesRx')
    1024
    >>> _get_ctr_multiplier('errorsRx')
    1
    """
    return 1024 if ctr_name.startswith("bytes") else 1


_CTR_TO_IF_FIELDS = {
    "bytesRx": "in_octets",  # is in Kilobytes!
    "packetsRx": "in_ucast",
    "multicastRx": "in_mcast",
    "broadcastRx": "in_bcast",
    "droppedRx": "in_discards",
    "errorsRx": "in_errors",
    "bytesTx": "out_octets",  # is in Kilobytes!
    "packetsTx": "out_ucast",
    "multicastTx": "out_mcast",
    "broadcastTx": "out_bcast",
    "droppedTx": "out_discards",
    "errorsTx": "out_errors",
}


def convert_esx_counters_if(section: Section) -> interfaces.Section:
    rates: Dict[str, Dict[str, int]] = {}
    mac_addresses: Dict[str, str] = {}

    for name, instances in section.items():
        if name.startswith("net."):
            for instance, values in instances.items():
                rates.setdefault(instance, {})
                if name == "net.macaddress":
                    mac_addresses[instance] = values[0][0][-1]
                else:
                    rates[instance][name[4:]] = int(average_parsed_data(values[0][0]))

    # Example of rates:
    # {
    #   'vmnic0': {
    #         'broadcastRx': 31,
    #         'broadcastTx': 0,
    #         'bytesRx': 3905,  # is in Kilobytes!
    #         'bytesTx': 134,
    #         'droppedRx': 0,
    #         'droppedTx': 0,
    #         'errorsRx': 0,
    #         'errorsTx': 0,
    #         'multicastRx': 5,
    #         'multicastTx': 1,
    #         'packetsRx': 53040,
    #         'packetsTx': 30822,
    #         'received': 3905,
    #         'transmitted': 134,
    #         'unknownProtos': 0,
    #         'usage': 4040,
    #         'state': 2,
    #         'bandwidth': 10000000,
    #     },
    # }
    # Example of mac_adresses:
    # {
    #   'vmnic0': 'AA:BB:CC:DD:EE:FF',
    # }

    return [
        interfaces.Interface(
            index=str(index),
            descr=name,
            alias=name,
            type="6",  # Ethernet
            speed=iface_rates.get("bandwidth", 0),
            oper_status=str(iface_rates.get("state", 1)),
            phys_address=interfaces.mac_address_from_hexstring(mac_addresses.get(name, "")),
            **{  # type: ignore[arg-type]
                if_field: iface_rates.get(ctr_name, 0) * _get_ctr_multiplier(ctr_name)
                for ctr_name, if_field in _CTR_TO_IF_FIELDS.items()
            },
        )
        for index, (name, iface_rates) in enumerate(sorted(rates.items()))
        if name  # Skip summary entry without interface name
    ]


def discover_esx_vsphere_counters_if(
    params: Sequence[Mapping[str, Any]],
    section: Section,
) -> DiscoveryResult:
    yield from interfaces.discover_interfaces(
        params,
        convert_esx_counters_if(section),
    )


def check_esx_vsphere_counters_if(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    if "net.bytesRx" not in section:
        raise IgnoreResultsError("Counter data is missing")
    yield from interfaces.check_multiple_interfaces(
        item,
        params,
        convert_esx_counters_if(section),
        input_is_rate=True,  # ESX does not send *counters* but *rates*
    )


register.check_plugin(
    name="esx_vsphere_counters_if",
    sections=["esx_vsphere_counters"],
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_esx_vsphere_counters_if,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_esx_vsphere_counters_if,
)


def discover_esx_vsphere_counters_diskio(section: Section) -> DiscoveryResult:
    if "" in section.get("disk.read", {}):
        yield Service(item="SUMMARY")


def _sum_instance_counts(counts: SubSectionCounter) -> float:
    summed_avgs = 0.0
    for data in counts.values():
        multivalues, _unit = data[0]
        summed_avgs += average_parsed_data(multivalues)
    return summed_avgs


def _max_latency(latencies: SubSectionCounter) -> Optional[int]:
    all_latencies: List[int] = []
    for data in latencies.values():
        multivalues, _unit = data[0]
        all_latencies.extend(map(int, multivalues))
    return max(all_latencies) if all_latencies else None


def check_esx_vsphere_counters_diskio(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    summary = {}

    for op_type in ("read", "write"):
        # summed up in key ""
        data = section.get("disk.%s" % op_type, {}).get("")
        multivalues, _unit = data[0] if data else (None, None)
        if multivalues is not None:
            summary["%s_throughput" % op_type] = average_parsed_data(multivalues) * 1024

        # sum up all instances
        op_counts_key = "disk.number%sAveraged" % op_type.title()
        if op_counts_key in section:
            summary["%s_ios" % op_type] = _sum_instance_counts(section[op_counts_key])

    latency = _max_latency(section.get("disk.deviceLatency", {}))
    if latency is not None:
        summary["latency"] = latency / 1000.0

    yield from diskstat.check_diskstat_dict(
        params=params,
        disk=summary,
        value_store=get_value_store(),
        this_time=time.time(),
    )


register.check_plugin(
    name="esx_vsphere_counters_diskio",
    sections=["esx_vsphere_counters"],
    service_name="Disk IO %s",
    discovery_function=discover_esx_vsphere_counters_diskio,
    check_function=check_esx_vsphere_counters_diskio,
    check_default_parameters={},
    check_ruleset_name="diskstat",
)
