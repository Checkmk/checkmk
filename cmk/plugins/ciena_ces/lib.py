#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from enum import Enum

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import all_of, any_of, contains, startswith


class SNMPEnum(Enum):
    @classmethod
    def good_value(cls) -> "SNMPEnum":
        raise NotImplementedError


class TceHealthStatus(SNMPEnum):
    unknown = "1"
    normal = "2"
    warning = "3"
    degraded = "4"
    faulted = "5"

    @classmethod
    def good_value(cls) -> "TceHealthStatus":
        return cls.normal


class PowerSupplyState(SNMPEnum):
    online = "1"
    faulted = "2"
    offline = "3"
    uninstalled = "4"

    @classmethod
    def good_value(cls) -> "PowerSupplyState":
        return cls.online


class FanStatus(SNMPEnum):
    ok = "1"
    pending = "2"
    rpmwarning = "3"
    uninstalled = "4"
    unknown = "9"

    @classmethod
    def good_value(cls) -> "FanStatus":
        return cls.ok


class LeoSystemState(SNMPEnum):
    normal = "1"
    warning = "2"
    degraded = "3"
    faulted = "4"

    @classmethod
    def good_value(cls) -> "LeoSystemState":
        return cls.normal


class LeoPowerSupplyState(SNMPEnum):
    online = "1"
    offline = "2"
    faulted = "3"

    @classmethod
    def good_value(cls) -> "LeoPowerSupplyState":
        return cls.online


class LeoFanStatus(SNMPEnum):
    ok = "1"
    pending = "2"
    failure = "3"

    @classmethod
    def good_value(cls) -> "LeoFanStatus":
        return cls.ok


class LeoTempSensorState(Enum):
    higher_than_threshold = "0"
    normal = "1"
    lower_than_threshold = "2"


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
