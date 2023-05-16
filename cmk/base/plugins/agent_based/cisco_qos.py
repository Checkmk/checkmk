#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

from collections.abc import Mapping
from dataclasses import dataclass
from typing import List

from .agent_based_api.v1 import all_of, contains, exists, OIDEnd, register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable


class InterfaceName(str):
    ...


class QoSClassName(str):
    ...


@dataclass(frozen=True)
class QosData:
    outbound_bits_counter: int
    dropped_bits_counter: int
    bandwidth: float
    policy_map_id: str
    policy_name: str | None


Section = Mapping[tuple[InterfaceName, QoSClassName], QosData]


def parse_cisco_qos(  # pylint: disable=too-many-branches
    string_table: List[StringTable],
) -> Section:
    ifs = dict(string_table[0])
    policies = dict(string_table[1])
    config = {".".join(oid.split(".")[-2:]): value for oid, value in string_table[3]}
    post_bytes = {".".join(oid.split(".")[-2:]): _saveint(value) for oid, value in string_table[4]}
    drop_bytes = {".".join(oid.split(".")[-2:]): _saveint(value) for oid, value in string_table[5]}
    if_names = dict(string_table[6])
    if_speeds = dict(string_table[7])
    parents = dict(string_table[8])
    if_qos_bandwidth = dict(string_table[9])
    if_qos_bandwidth_units = dict(string_table[10])
    object_types = dict(string_table[11])

    parent_value_cache = {a_value: a_key.split(".")[1] for a_key, a_value in config.items()}
    section = {}

    for class_id, class_name in string_table[2]:
        for policy_id, objects_id in _get_config_entries_by_class_id(config, class_id):
            if not (if_index := ifs.get(policy_id)):
                continue

            if (if_name := if_names.get(if_index)) is None:
                continue

            policy_map_id = None
            # Get the policy_map_id. To retrieve this get one of the config entries
            # of type "policy map" from the config table. All of this type should have
            # the same value, which is then the policy_map_id.
            for key in object_types:
                if key.startswith(policy_id + ".") and object_types[key] == "1":
                    policy_map_id = config[key]
                    break

            if policy_map_id is None:
                continue

            speed: float = _saveint(if_speeds[if_index])

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
                            qos_unit = int(if_qos_bandwidth_units[config[b_key]])
                            qos_bandwidth = _saveint(if_qos_bandwidth[config[b_key]])
                            if qos_unit == 1:
                                speed = qos_bandwidth * 1000

                            elif qos_unit == 2:
                                speed = speed * (qos_bandwidth / 100.0)

                            elif qos_unit == 3:
                                remaining = speed * (qos_bandwidth / 100.0)
                                speed = speed - remaining
                            break
                        except KeyError:
                            pass

            section[(InterfaceName(if_name), QoSClassName(class_name))] = QosData(
                outbound_bits_counter=post_bytes.get(policy_id + "." + objects_id, 0) * 8,
                dropped_bits_counter=drop_bytes.get(policy_id + "." + objects_id, 0) * 8,
                bandwidth=speed,
                policy_map_id=policy_map_id,
                policy_name=policies.get(policy_map_id),
            )

    return section


def _saveint(i: str, /) -> int:
    try:
        return int(i)
    except ValueError:
        return 0


def _get_config_entries_by_class_id(config: Mapping[str, str], class_id: str) -> list[list[str]]:
    return [if_index.split(".") for if_index, value in config.items() if value == class_id]


register.snmp_section(
    name="cisco_qos",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"), exists(".1.3.6.1.4.1.9.9.166.1.1.1.1.4.*")
    ),
    parse_function=parse_cisco_qos,
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
)
