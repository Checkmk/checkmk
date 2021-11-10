#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import Enum
from typing import Mapping

from ..agent_based_api.v1 import all_of, any_of, contains, startswith
from ..agent_based_api.v1.type_defs import StringTable


class OperState(Enum):
    enabled = "1"
    disabled = "2"


OperStateSection = Mapping[str, OperState]


def parse_ciena_oper_state(string_table: StringTable) -> OperStateSection:
    """
    >>> from pprint import pprint
    >>> string_table = [['TN_mz0100-mz0300_1_p', '1'],
    ... ['TN_mz0100-mz0300_2_p', '1'],
    ... ['TN_mz0100-mz04-02_p_B', '1']]
    >>> pprint(parse_ciena_oper_state(string_table))
    {'TN_mz0100-mz0300_1_p': <OperState.enabled: '1'>,
     'TN_mz0100-mz0300_2_p': <OperState.enabled: '1'>,
     'TN_mz0100-mz04-02_p_B': <OperState.enabled: '1'>}
    """

    return {item: OperState(oper_state) for item, oper_state in string_table if oper_state}


OID_SysDescID = ".1.3.6.1.2.1.1.1.0"
OID_SysObjectID = ".1.3.6.1.2.1.1.2.0"

DETECT_CIENA = any_of(
    startswith(OID_SysObjectID, ".1.3.6.1.4.1.1271.1.2.11"),
    startswith(OID_SysObjectID, ".1.3.6.1.4.1.6141.1.96"),
)

DETECT_CIENA_5171 = all_of(
    DETECT_CIENA,
    contains(OID_SysDescID, "5171"),
)

DETECT_CIENA_5142 = all_of(
    DETECT_CIENA,
    contains(OID_SysDescID, "5142"),
)
