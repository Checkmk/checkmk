#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Dict,
    List,
    Tuple,
)
from .agent_based_api.v0 import (
    register,
    type_defs,
)

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

Section = Dict[str, Dict[str, List[Tuple[List[str], str]]]]


def parse_esx_vsphere_counters(string_table: type_defs.AgentStringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_esx_vsphere_counters([
    ... ['disk.numberRead', 'naa.5000cca05688e814', '0#0', 'number'],
    ... ['disk.write',
    ...  'naa.6000eb39f31c58130000000000000015',
    ...  '0#0',
    ...  'kiloBytesPerSecond'],
    ... ['net.bytesRx', 'vmnic0', '1#1', 'kiloBytesPerSecond'],
    ... ['net.droppedRx', 'vmnic1', '0#0', 'number'],
    ... ['net.errorsRx', '', '0#0', 'number'],
    ... ]))
    {'disk.numberRead': {'naa.5000cca05688e814': [(['0', '0'], 'number')]},
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
