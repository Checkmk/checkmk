#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

from ..agent_based_api.v1 import type_defs

# TODO
# Use 'status-numeric' instead of 'status' field regardless of language.
# See for state mapping: https://support.hpe.com/hpsc/doc/public/display?docId=emr_na-a00017709en_us

Object = Dict[str, str]
Section = Dict[str, Object]


def _parse_hp_msa_objects(string_table: type_defs.StringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(_parse_hp_msa_objects([
    ... ['port', '3', 'durable-id', 'hostport_A1'],
    ... ['port', '3', 'controller', 'A'],
    ... ['port', '3', 'controller-numeric', '1'],
    ... ['port', '5', 'durable-id', 'hostport_A2'],
    ... ['port', '5', 'controller', 'A'],
    ... ['port', '5', 'controller-numeric', '1'],
    ... ]))
    {'hostport_A1': {'controller': 'A',
                     'controller-numeric': '1',
                     'item_type': 'port'},
     'hostport_A2': {'controller': 'A',
                     'controller-numeric': '1',
                     'item_type': 'port'}}
    """
    info_enrolment: Section = {}
    item_id = None
    for line in string_table:
        if line[2] == "durable-id":  # marks start of new object
            item_id = " ".join(line[3:])
            info_enrolment.setdefault(item_id, {"item_type": line[0]})
        elif item_id:
            info_enrolment[item_id][line[2]] = " ".join(line[3:])
    return info_enrolment


def _get_hp_msa_object_item(
    key: str,
    data: Object,
) -> str:
    """
    >>> from pprint import pprint
    >>> pprint(_get_hp_msa_object_item('key', {}))
    'key'
    >>> pprint(_get_hp_msa_object_item('key', {'location': 'location'}))
    'location'
    """
    item = data.get("location", key).replace("- ", "")
    return item.rsplit("_", 1)[-1].strip()


def parse_hp_msa(string_table: type_defs.StringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_hp_msa([
    ... ['port', '3', 'durable-id', 'hostport_A1'],
    ... ['port', '3', 'controller', 'A'],
    ... ['port', '3', 'controller-numeric', '1'],
    ... ['port', '5', 'durable-id', 'hostport_A2'],
    ... ['port', '5', 'controller', 'A'],
    ... ['port', '5', 'controller-numeric', '1'],
    ... ]))
    {'A1': {'controller': 'A', 'controller-numeric': '1', 'item_type': 'port'},
     'A2': {'controller': 'A', 'controller-numeric': '1', 'item_type': 'port'}}
    """
    return {
        _get_hp_msa_object_item(key, data): data
        for key, data in _parse_hp_msa_objects(string_table).items()
    }
