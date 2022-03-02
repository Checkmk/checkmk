#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, Sequence, Union

from .agent_based_api.v1 import OIDBytes, register, SNMPTree, startswith, type_defs
from .utils import if64, interfaces

mcdata_fcport_speedbits = {"2": 1000000000, "3": 2000000000}
mcdata_fcport_opstatus = {"1": "1", "2": "2", "3": "testing", "4": "faulty"}


def _bin_to_64(bin_: Union[str, Sequence[int]]) -> int:
    """
    >>> _bin_to_64([1])
    1
    >>> _bin_to_64([2, 3])
    533
    """
    return sum(b * 265**i for i, b in enumerate(bin_[::-1]))


def _line_to_interface(line: Iterable[Union[str, Sequence[int]]]) -> interfaces.Interface:
    index, opStatus, speed, txWords64, rxWords64, txFrames64, rxFrames64, c3Discards64, crcs = line
    index = "%02d" % int(str(index))
    return interfaces.Interface(
        index=index,
        descr=index,
        alias=index,
        type="6",
        speed=mcdata_fcport_speedbits.get(str(speed), 0),
        oper_status=mcdata_fcport_opstatus.get(str(opStatus), "unknown"),
        in_octets=_bin_to_64(rxWords64) * 4,
        in_ucast=_bin_to_64(rxFrames64),
        in_errors=int(str(crcs)),
        out_octets=_bin_to_64(txWords64) * 4,
        out_ucast=_bin_to_64(txFrames64),
        out_discards=_bin_to_64(c3Discards64),
    )


def parse_mcdata_fcport(string_table: type_defs.StringByteTable) -> interfaces.Section:
    return [_line_to_interface(line) for line in string_table]


register.snmp_section(
    name="mcdata_fcport",
    parse_function=parse_mcdata_fcport,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.289.2.1.1.2.3.1.1",
        oids=[
            "1",  # EF-6000-MIB::ef6000PortIndex
            "3",  # EF-6000-MIB::ef6000PortOpStatus
            "11",  # EF-6000-MIB::ef6000PortSpeed
            OIDBytes("67"),  # EF-6000-MIB::ef6000PortTxWords64
            OIDBytes("68"),  # EF-6000-MIB::ef6000PortRxWords64
            OIDBytes("69"),  # EF-6000-MIB::ef6000PortTxFrames64
            OIDBytes("70"),  # EF-6000-MIB::ef6000PortRxFrames64
            OIDBytes("83"),  # EF-6000-MIB::ef6000PortC3Discards64
            "65",  # EF-6000-MIB::ef6000PortCrcs
        ],
    ),
    # check if number of network interfaces (IF-MIB::ifNumber.0) is at least 2
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.289."),
)

register.check_plugin(
    name="mcdata_fcport",
    service_name="Port %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=interfaces.discover_interfaces,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=if64.generic_check_if64,
    cluster_check_function=interfaces.cluster_check,
)
