#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

import time
from typing import Literal

from cmk.base.check_api import (
    get_average,
    get_nic_speed_human_readable,
    get_rate,
    LegacyCheckDefinition,
    savefloat,
    saveint,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    all_of,
    contains,
    exists,
    OIDEnd,
    render,
    SNMPTree,
)

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


def cisco_qos_get_config_entries_by_class_id(config, class_id):
    return [if_index.split(".") for if_index, value in config.items() if value == class_id]


def inventory_cisco_qos(info):
    if len(info) == 12:
        ifs = dict(info[0])
        config = {".".join(oid.split(".")[-2:]): value for oid, value in info[3]}
        if_names = dict(info[6])

        # Find all interfaces for each class and create one service for each pair
        items = []
        for class_id, class_name in info[2]:
            # Get interface ids which use this qos class
            for policy_id, _objects_id in cisco_qos_get_config_entries_by_class_id(
                config, class_id
            ):
                if ifs.get(policy_id) in if_names:
                    if_name = if_names[ifs[policy_id]]
                    items += [("%s: %s" % (if_name, class_name), {})]

        return items
    return []


def check_cisco_qos(item, params, info):  # pylint: disable=too-many-branches
    unit = params.get("unit", "bit")
    average = params.get("average")
    post_warn, post_crit = params.get("post", (None, None))
    drop_warn, drop_crit = params.get("drop", (None, None))

    # Load values and format them
    ifs = dict(info[0])
    policies = dict(info[1])
    classes = dict(info[2])
    config = {".".join(oid.split(".")[-2:]): value for oid, value in info[3]}
    post_bytes = {".".join(oid.split(".")[-2:]): value for oid, value in info[4]}
    drop_bytes = {".".join(oid.split(".")[-2:]): value for oid, value in info[5]}
    if_names = dict(info[6])
    if_speeds = dict(info[7])
    parents = dict(info[8])
    if_qos_bandwidth = dict(info[9])
    if_qos_bandwidth_units = dict(info[10])
    object_types = dict(info[11])

    if_name, class_name = item.split(": ")

    # Gather the class id by class_name
    class_id = None
    for cid, cname in classes.items():
        if class_name == cname:
            class_id = cid
            break

    # Gather the interface id by class_name
    if_id = None
    for iid2 in ifs.values():
        if if_name == if_names.get(iid2):
            if_id = iid2
            break

    if not if_id or not class_id:
        return (3, "QoS class not found for that interface")

    policy_id, objects_id, policy_map_id, policy_name = None, None, None, None
    for this_policy_id, this_objects_id in cisco_qos_get_config_entries_by_class_id(
        config, class_id
    ):
        if if_id != ifs[this_policy_id]:
            continue  # skip the ones of other interfaces

        # Get the policy_map_id. To retrieve this get one of the config entries
        # of type "policy map" from the config table. All of this type should have
        # the same value, which is then the policy_map_id.
        for key in object_types:
            if key.startswith(this_policy_id + ".") and object_types[key] == "1":
                policy_map_id = config[key]
                break

        if policy_map_id is None:
            return 3, "Invalid policy map id"

        policy_name = policies.get(policy_map_id)
        policy_id = this_policy_id
        objects_id = this_objects_id

    if policy_id is None or objects_id is None:
        return 3, "Could not find policy_id or objects_id"

    post_b = post_bytes.get(policy_id + "." + objects_id, 0)
    drop_b = drop_bytes.get(policy_id + "." + objects_id, 0)
    speed = savefloat(if_speeds[if_id])

    parent_value_cache = {a_value: a_key.split(".")[1] for a_key, a_value in config.items()}

    # if a_value == class_id:
    #     parent_value = a_key.split(".")[1]
    for b_key, b_value in parents.items():
        if parent_value_cache[class_id] == b_value:
            if object_types[b_key] == "4":
                try:
                    # 1 kbps
                    # 2 percentage
                    # 3 percentageRemaining
                    # 4 ratioRemaining
                    # 5 perThousand
                    # 6 perMillion
                    qos_unit = float(if_qos_bandwidth_units[config[b_key]])
                    qos_bandwidth = savefloat(if_qos_bandwidth[config[b_key]])
                    if qos_unit == 1:
                        speed = qos_bandwidth * 1000.0

                    elif qos_unit == 2:
                        speed = speed * (qos_bandwidth / 100.0)

                    elif qos_unit == 3:
                        remaining = speed * (qos_bandwidth / 100.0)
                        speed = speed - remaining
                    break
                except KeyError:
                    pass

    # Bandwidth needs to be in bytes for later calculations
    bw = speed / 8.0

    # Determine post warn/crit levels
    post_warn, post_crit = _compute_thresholds((post_warn, post_crit), bw, unit)

    # Determine drop warn/crit levels
    drop_warn, drop_crit = _compute_thresholds((drop_warn, drop_crit), bw, unit)

    # Handle counter values
    state = 0
    infotext = ""
    this_time = time.time()
    rates = []
    perfdata = []
    perfdata_avg = []

    for name, counter, warn, crit, min_val, max_val in [
        ("post", post_b, post_warn, post_crit, 0.0, bw),
        ("drop", drop_b, drop_warn, drop_crit, 0.0, bw),
    ]:
        rate = get_rate("cisco_qos.%s.%s" % (name, item), this_time, saveint(counter))
        rates.append(rate)
        perfdata.append((name, rate, warn, crit, min_val, max_val))

        if average:
            avg_value = get_average("cisco_qos.%s.%s.avg" % (name, item), this_time, rate, average)
            rates.append(avg_value)
            perfdata_avg.append(
                ("%s_avg_%d" % (name, average), avg_value, warn, crit, min_val, max_val)
            )

    perfdata.extend(perfdata_avg)

    def format_value(value):
        if unit == "bit":
            value = value * 8
            return get_nic_speed_human_readable(value)
        return render.iobandwidth(value)

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

    if policy_name:
        infotext += ", Policy-Name: %s, Int-Bandwidth: %s" % (policy_name, format_value(bw))
    else:
        infotext += ", Policy-Map-ID: %s, Int-Bandwidth: %s" % (policy_map_id, format_value(bw))
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
        if unit == "bit":
            return raw_thresholds[0] / 8, raw_thresholds[1] / 8
        return raw_thresholds
    return raw_thresholds


check_info["cisco_qos"] = LegacyCheckDefinition(
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"), exists(".1.3.6.1.4.1.9.9.166.1.1.1.1.4.*")
    ),
    service_name="QoS %s",
    check_function=check_cisco_qos,
    discovery_function=inventory_cisco_qos,
    check_ruleset_name="cisco_qos",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.166.1.1.1.1",
            oids=[OIDEnd(), "4"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.166.1.6.1.1",
            oids=[OIDEnd(), "1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.166.1.7.1.1",
            oids=[OIDEnd(), "1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.166.1.5.1.1",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.166.1.15.1.1",
            oids=[OIDEnd(), "9"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.166.1.15.1.1",
            oids=[OIDEnd(), "16"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.2.2.1",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.2.2.1",
            oids=[OIDEnd(), "5"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.166.1.5.1.1",
            oids=[OIDEnd(), "4"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.166.1.9.1.1",
            oids=[OIDEnd(), "1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.166.1.9.1.1",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.166.1.5.1.1",
            oids=[OIDEnd(), "3"],
        ),
    ],
    check_default_parameters={"drop": (0.01, 0.01)},
)
