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
from enum import Enum
from typing import List

from .agent_based_api.v1 import all_of, contains, exists, OIDEnd, register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable


class InterfaceName(str):
    ...


class cbQosCMName(str):
    ...


class cbQosConfigIndex(str):
    ...


class cbQosPolicyMapName(str):
    ...


@dataclass(frozen=True)
class QosData:
    outbound_bits_counter: int
    dropped_bits_counter: int
    bandwidth: float
    policy_map_index: cbQosConfigIndex
    policy_map_name: cbQosPolicyMapName | None


Section = Mapping[tuple[InterfaceName, cbQosCMName], QosData]


def parse_cisco_qos(  # pylint: disable=too-many-branches
    string_table: List[StringTable],
) -> Section:
    policy_index_to_interface_index = {
        _cbQosPolicyIndex(pol_id): _InterfaceIndex(if_idx) for pol_id, if_idx in string_table[0]
    }
    config_index_to_policy_name = {
        cbQosConfigIndex(pol_id): cbQosPolicyMapName(pol_name)
        for pol_id, pol_name in string_table[1]
    }
    policy_and_object_index_to_config_index = {
        _oid_end_to_policy_and_object_index(oid_end): cbQosConfigIndex(cfg_idx)
        for oid_end, cfg_idx in string_table[3]
    }
    policy_and_object_index_to_outbound_bytes_counters = {
        _oid_end_to_policy_and_object_index(oid_end): _saveint(counter)
        for oid_end, counter in string_table[4]
    }
    policy_and_object_index_to_dropped_bytes_counters = {
        _oid_end_to_policy_and_object_index(oid_end): _saveint(counter)
        for oid_end, counter in string_table[5]
    }
    interface_index_to_interface_name = {
        _InterfaceIndex(if_idx): InterfaceName(if_name) for if_idx, if_name in string_table[6]
    }
    interface_index_to_interface_speed = {
        _InterfaceIndex(if_idx): _saveint(if_speed) for if_idx, if_speed in string_table[7]
    }
    policy_and_object_index_to_parent_index = {
        _oid_end_to_policy_and_object_index(oid_end): _cbQosObjectsIndex(parent_idx)
        for oid_end, parent_idx in string_table[8]
    }
    config_index_to_bandwidth = {
        cbQosConfigIndex(cfg_idx): _saveint(bandwidth) for cfg_idx, bandwidth in string_table[9]
    }
    config_index_to_bandwidth_units = {
        cbQosConfigIndex(cfg_idx): _QueueingBandwidthUnits(bandwidth_unit)
        for cfg_idx, bandwidth_unit in string_table[10]
    }
    policy_and_object_index_to_object_type = {
        _oid_end_to_policy_and_object_index(oid_end): _QosObjectType(obj_type)
        for oid_end, obj_type in string_table[11]
    }

    config_index_to_object_index = {
        cfg_idex: obj_idx
        for (_pol_idx, obj_idx), cfg_idex in policy_and_object_index_to_config_index.items()
    }
    section = {}

    for config_index, class_name in (
        (
            cbQosConfigIndex(raw_config_index),
            cbQosCMName(raw_class_name),
        )
        for raw_config_index, raw_class_name in string_table[2]
    ):
        for policy_index, object_index in (
            policy_and_object_idx
            for policy_and_object_idx, cfg_index in policy_and_object_index_to_config_index.items()
            if cfg_index == config_index
        ):
            if not (if_index := policy_index_to_interface_index.get(policy_index)):
                continue

            if (if_name := interface_index_to_interface_name.get(if_index)) is None:
                continue

            try:
                policy_map_idx = next(
                    policy_and_object_index_to_config_index[(pol_idx, obj_idx)]
                    for (pol_idx, obj_idx), type_ in policy_and_object_index_to_object_type.items()
                    if pol_idx == policy_index and type_ is _QosObjectType.POLICYMAP
                )
            except StopIteration:
                continue

            speed: float = interface_index_to_interface_speed[if_index]

            for pol_and_obj_idx, parent_idx in policy_and_object_index_to_parent_index.items():
                if config_index_to_object_index[config_index] == parent_idx:
                    if (
                        policy_and_object_index_to_object_type[pol_and_obj_idx]
                        is _QosObjectType.QUEUEING
                    ):
                        try:
                            qos_unit = config_index_to_bandwidth_units[
                                policy_and_object_index_to_config_index[pol_and_obj_idx]
                            ]
                            qos_bandwidth = config_index_to_bandwidth[
                                policy_and_object_index_to_config_index[pol_and_obj_idx]
                            ]
                        except KeyError:
                            continue

                        match qos_unit:
                            case _QueueingBandwidthUnits.KBPS:
                                speed = qos_bandwidth * 1000
                            case _QueueingBandwidthUnits.PERCENTAGE:
                                speed *= qos_bandwidth / 100
                            case _QueueingBandwidthUnits.PERCENTAGE_REMAINING:
                                speed *= 1 - (qos_bandwidth / 100)

                        break

            section[(if_name, class_name)] = QosData(
                outbound_bits_counter=policy_and_object_index_to_outbound_bytes_counters.get(
                    (policy_index, object_index), 0
                )
                * 8,
                dropped_bits_counter=policy_and_object_index_to_dropped_bytes_counters.get(
                    (policy_index, object_index), 0
                )
                * 8,
                bandwidth=speed,
                policy_map_index=policy_map_idx,
                policy_map_name=config_index_to_policy_name.get(policy_map_idx),
            )

    return section


class _cbQosPolicyIndex(str):
    ...


class _InterfaceIndex(str):
    ...


class _cbQosObjectsIndex(str):
    ...


def _oid_end_to_policy_and_object_index(
    oid_end: str, /
) -> tuple[_cbQosPolicyIndex, _cbQosObjectsIndex]:
    oid_split = oid_end.split(".")
    return _cbQosPolicyIndex(oid_split[-2]), _cbQosObjectsIndex(oid_split[-1])


def _saveint(i: str, /) -> int:
    try:
        return int(i)
    except ValueError:
        return 0


# https://www.circitor.fr/Mibs/Html/C/CISCO-CLASS-BASED-QOS-MIB.php#QosObjectType
class _QosObjectType(Enum):
    POLICYMAP = "1"
    CLASSMAP = "2"
    MATCH_STATEMENT = "3"
    QUEUEING = "4"
    RANDOM_DETECT = "5"
    TRAFFIC_SHAPING = "6"
    POLICE = "7"
    SET = "8"
    COMPRESSION = "9"
    IPSLA_MEASURE = "10"
    ACCOUNT = "11"


# https://www.circitor.fr/Mibs/Html/C/CISCO-CLASS-BASED-QOS-MIB.php#QueueingBandwidthUnits
class _QueueingBandwidthUnits(Enum):
    KBPS = "1"
    PERCENTAGE = "2"
    PERCENTAGE_REMAINING = "3"
    RATIO_REMAINING = "4"
    PER_THOUSAND = "5"
    PER_MILLION = "6"
    # not part of the MIB, but observed in reality (walk from SUP-14099)
    _UNKNOWN = "0"


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
