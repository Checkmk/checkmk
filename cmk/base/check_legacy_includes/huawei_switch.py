#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List, NamedTuple, Optional

from cmk.base.check_api import OID_END


def huawei_switch_scan_function(oid):
    return ".1.3.6.1.4.1.2011.2.23" in oid(".1.3.6.1.2.1.1.2.0")


def huawei_entity_specific_snmp_info(snmp_info):
    """
    Used for the 'snmp_info' of a check to retrieve values that are indexed by a
    entPhyisicalIndex. See parse_huawei_physical_entity_values() for a detailed description.
    """
    return [
        (
            ".1.3.6.1.2.1.47.1.1.1.1",
            [OID_END, "7"],
        ),  # retrieve list of [entPhysicalIndex, entPhysicalName]
        snmp_info,
    ]


huawei_mpu_board_name_start = "mpu board"


class HuaweiPhysicalEntityValue(NamedTuple):
    physical_index: str
    stack_member: int
    value: Optional[str]


def parse_huawei_physical_entity_values(info, entity_name_start=huawei_mpu_board_name_start):
    """
    Parses the info structure retrieved by using the huawei_entity_specific_snmp_info() function
    for the 'snmp_info' of a check. This info structure will contain two lists of lists.

    The first list has a structure like this:
    [
        [u'67108867', u'HUAWEI S6720 Routing Switch'],
        [u'67108869', u'Board slot 0'],
        [u'68157445', u'Board slot 1'],
        [u'68157449', u'MPU Board 1'],
        [u'68173836', u'Card slot 1/1'],
        [u'68190220', u'Card slot 1/2'],
        [u'68206604', u'Card slot 1/3'],
        [u'68222988', u'Card slot 1/4'],
        [u'68239372', u'Card slot 1/5'],
        [u'68239373', u'POWER Card 1/PWR1'],
        [u'68255756', u'Card slot 1/6'],
        [u'68255757', u'POWER Card 1/PWR2'],
        [u'69206025', u'MPU Board 2'],
        ...
    ]

    The entity_name_start argument is used to string match (case insensitive) against the
    start of the entity names in this list.

    For all names that are matching, the corresponding 'entPhysicalIndex' is stored
    (e.g. 68157449 and 69206025 when searching for 'mpu board') and the matching values
    in the second list are looked up.
    The second list contains the values and has a structure like this:

    [
        [u'67108867', u'0'],
        [u'67108869', u'0'],
        [u'68157445', u'0'],
        [u'68157449', u'22'],
        [u'68173836', u'0'],
        [u'69206021', u'0'],
        [u'69206025', u'52'],
        [u'69222412', u'0'],
        ...
    ]

    So for the 'mpu board' example we would retrieve the two values 22 and 52.

    Returns a dict of the form:
    {
        'item name': HuaweiPhysicalEntityValue(...)
        ...
    }
    """
    entities_info, values_info = info
    stack_member_number = 0
    # groups entities per stack member
    entities_per_member: Dict[int, List[HuaweiPhysicalEntityValue]] = {}

    for entity_line in entities_info:
        lower_entity_name = entity_line[1].lower()
        ent_physical_index = entity_line[0]

        # each mpu board signals the beginning of a new stack member
        if lower_entity_name.startswith(huawei_mpu_board_name_start):
            stack_member_number += 1
            entities_per_member[stack_member_number] = []

        if lower_entity_name.startswith(entity_name_start.lower()):
            value = None
            for value_line in values_info:
                if value_line[0] == ent_physical_index:
                    value = value_line[1]

            entities_per_member[stack_member_number].append(
                HuaweiPhysicalEntityValue(
                    physical_index=ent_physical_index,
                    stack_member=stack_member_number,
                    value=value,
                )
            )

    multiple_entities_per_member = entity_name_start != huawei_mpu_board_name_start
    return huawei_item_dict_from_entities(entities_per_member, multiple_entities_per_member)


def huawei_item_dict_from_entities(entities_per_member, multiple_entities_per_member=True):
    """
    Converts a dictionary of the form:
    {
        stack_member_number1:  [entity1_1, entity1_2, ...],
        stack_member_number2:  [entity2_1, entity2_2, ...],
        ...
    }

    into a dictionary of the form:
    {
        'item name': entity1_1
        'item name': entity1_2
        ...
        'item name': entity2_1
        'item name': entity2_2
        ...
    }

    Where 'item name' has the form {stack_memer_number}/{entity_number} if multiple_entites_per_member is True.
    Otherwise it is expected that each member has only one entity and 'item name' is just {stack_member_number}.
    """
    items = {}
    for member_number, entities in entities_per_member.items():
        for entity_idx, entity in enumerate(entities):
            item_name = str(member_number)

            # add sub index if there are multiple entities per stack member possible
            if multiple_entities_per_member:
                item_name += "/" + str(entity_idx + 1)

            items[item_name] = entity
    return items
