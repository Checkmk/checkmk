#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Iterator, Mapping
from typing import Any, Literal

from cmk.base.check_api import (
    get_average,
    get_nic_speed_human_readable,
    get_rate,
    LegacyCheckDefinition,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import render
from cmk.base.plugins.agent_based.cisco_qos import InterfaceName, QoSClassName, Section

# Author: Lars Michelsen <lm@mathias-kettner.de>

# Relevant SNMP OIDs:
# .1.3.6.1.4.1.9.9.166.1.1.1.1.4.144 9
# .1.3.6.1.4.1.9.9.166.1.1.1.1.4.258 16
# .1.3.6.1.4.1.9.9.166.1.1.1.1.4.400 25
#
# .1.3.6.1.4.1.9.9.166.1.6.1.1.1.3974704 "6cos"
# .1.3.6.1.4.1.9.9.166.1.6.1.1.1.6208592 "ingress-map"
#
# .1.3.6.1.4.1.9.9.166.1.7.1.1.1.1593 "class-default"
# .1.3.6.1.4.1.9.9.166.1.7.1.1.1.18785 "EF"
# .1.3.6.1.4.1.9.9.166.1.7.1.1.1.284945 "AF1"
# .1.3.6.1.4.1.9.9.166.1.7.1.1.1.284961 "AF2"
# .1.3.6.1.4.1.9.9.166.1.7.1.1.1.284977 "AF3"

# http://www.oidview.com/mibs/9/CISCO-CLASS-BASED-QOS-MIB.html

# TEST:
#
# search class table:
# .1.3.6.1.4.1.9.9.166.1.7.1.1.1.284945 (cbQosCMName) "AF1"
# class_id = 284945 (cbQosConfigIndex)
#
# search config table for matching value
# .1.3.6.1.4.1.9.9.166.1.5.1.1.2.144.5256 284945
# key = 144.5256 (cbQosPolicyIndex: 144, cbQosObjectsIndex: 5256)
#
# search if table for matchin if_id: 144
# .1.3.6.1.4.1.9.9.166.1.1.1.1.4.144 (cbQosIfIndex) 9
# if_policy = 9 (ifIndex -> standard mib)
#
# get config_id from config table using if_id.if_id 144.144
# .1.3.6.1.4.1.9.9.166.1.5.1.1.2.144.144 (cbQosConfigIndex) 6208592
# config_index = 6208592
#
# get policy name using the policy_index
# .1.3.6.1.4.1.9.9.166.1.6.1.1.1.6208592 "ingress-map"
# policy_name = "ingress-map"
#
# get post bytes using the key
# .1.3.6.1.4.1.9.9.166.1.15.1.1.9.144.5256 0
# post_bytes = 0
#
# get dropped bytes using the key
# .1.3.6.1.4.1.9.9.166.1.15.1.1.16.144.5256 0
# dropped_bytes = 0
#
# get if_name using the if_policy: 9
# .1.3.6.1.2.1.31.1.1.1.1.9 Vl1
# if_name = Vl1
#
# get if_speed using the if_policy: 9
# .1.3.6.1.2.1.2.2.1.5.9 100000000
# if_speed = 100000000
#
###
# Test to find the badwidth of the classes. Not finished...
#
# 'cbQosObjectsType' => {
#         1 => 'policymap',
#         2 => 'classmap',
#         3 => 'matchStatement',
#         4 => 'queueing',
#         5 => 'randomDetect',
#         6 => 'trafficShaping',
#         7 => 'police',
#         8 => 'set' },
#
# Index:
# .1.3.6.1.4.1.9.9.166.1.5.1.1.2.258.1244739 1608
#
# Type:
# .1.3.6.1.4.1.9.9.166.1.5.1.1.3.258.1244739 4
#
# Parent ID:
# .1.3.6.1.4.1.9.9.166.1.5.1.1.4.258.1244739 6184
#
# cbQosQueueingStatsEntry:
# .1.3.6.1.4.1.9.9.166.1.18.1.1.2.258.1244739 64
# ...

# Index:
# .1.3.6.1.4.1.9.9.166.1.5.1.1.2.258.6184 18785
# Type:
# .1.3.6.1.4.1.9.9.166.1.5.1.1.3.258.6184 2
# Parent ID:
# .1.3.6.1.4.1.9.9.166.1.5.1.1.4.258.6184 258

# get cbQosQueueingCfgBandwidth
# .1.3.6.1.4.1.9.9.166.1.9.1.1.1.1608 3094


def inventory_cisco_qos(section: Section) -> Iterator[tuple[str, dict]]:
    yield from ((f"{if_name}: {class_name}", {}) for if_name, class_name in section)


def check_cisco_qos(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> object:
    unit = params.get("unit", "bit")
    average = params.get("average")
    post_warn, post_crit = params.get("post", (None, None))
    drop_warn, drop_crit = params.get("drop", (None, None))

    raw_if_name, raw_class_name = item.split(": ")

    if not (qos_data := section.get((InterfaceName(raw_if_name), QoSClassName(raw_class_name)))):
        return None

    # Determine post warn/crit levels
    post_warn, post_crit = _compute_thresholds((post_warn, post_crit), qos_data.bandwidth, unit)

    # Determine drop warn/crit levels
    drop_warn, drop_crit = _compute_thresholds((drop_warn, drop_crit), qos_data.bandwidth, unit)

    # Handle counter values
    state = 0
    infotext = ""
    this_time = time.time()
    rates = []
    perfdata = []

    for name, counter, warn, crit, min_val, max_val in [
        (
            "qos_outbound_bits_rate",
            qos_data.outbound_bits_counter,
            post_warn,
            post_crit,
            0.0,
            qos_data.bandwidth,
        ),
        (
            "qos_dropped_bits_rate",
            qos_data.dropped_bits_counter,
            drop_warn,
            drop_crit,
            0.0,
            qos_data.bandwidth,
        ),
    ]:
        rate = get_rate("cisco_qos.%s.%s" % (name, item), this_time, counter)
        rates.append(rate)
        perfdata.append((name, rate, warn, crit, min_val, max_val))

        if average:
            avg_value = get_average("cisco_qos.%s.%s.avg" % (name, item), this_time, rate, average)
            rates.append(avg_value)

    def format_value(value):
        if unit == "bit":
            return get_nic_speed_human_readable(value)
        return render.iobandwidth(value / 8)

    if average:
        post_rate = rates[1]
        drop_rate = rates[3]
    else:
        post_rate = rates[0]
        drop_rate = rates[1]

    for what, rate, warn, crit in [
        ("post", post_rate, post_warn, post_crit),
        ("drop", drop_rate, drop_warn, drop_crit),
    ]:
        infotext += ", %s: %s" % (what, format_value(rate))
        if crit is not None and rate >= crit:
            state = max(2, state)
            infotext += "(!!)"
        elif warn is not None and rate >= warn:
            state = max(1, state)
            infotext += "(!)"

    if qos_data.policy_name:
        infotext += ", Policy-Name: %s, Int-Bandwidth: %s" % (
            qos_data.policy_name,
            format_value(qos_data.bandwidth),
        )
    else:
        infotext += ", Policy-Map-ID: %s, Int-Bandwidth: %s" % (
            qos_data.policy_map_id,
            format_value(qos_data.bandwidth),
        )
    return (state, infotext.lstrip(", "), perfdata)


def _compute_thresholds(
    raw_thresholds: tuple[float, float] | tuple[None, None],
    bandwidth: float,
    unit: Literal["bit", "byte"],
) -> tuple[float, float] | tuple[None, None]:
    if isinstance(raw_thresholds[0], float):
        if bandwidth:
            return bandwidth * raw_thresholds[0] / 100, bandwidth * raw_thresholds[1] / 100
        return None, None
    if isinstance(raw_thresholds[0], int):
        if unit == "byte":
            return raw_thresholds[0] * 8, raw_thresholds[1] * 8
        return raw_thresholds
    return raw_thresholds


check_info["cisco_qos"] = LegacyCheckDefinition(
    service_name="QoS %s",
    check_function=check_cisco_qos,
    discovery_function=inventory_cisco_qos,
    check_ruleset_name="cisco_qos",
    check_default_parameters={"drop": (0.01, 0.01)},
)
