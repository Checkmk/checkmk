#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Iterable,
    Sequence,
    Union,
)
from .agent_based_api.v1 import (
    OIDBytes,
    register,
    SNMPTree,
    startswith,
    type_defs,
)
from .utils import (
    if64,
    interfaces,
)

mcdata_fcport_speedbits = {"2": 1000000000, "3": 2000000000}
mcdata_fcport_opstatus = {"1": "1", "2": "2", "3": "testing", "4": "faulty"}


def _bin_to_64(bin_: Union[str, Sequence[int]]) -> int:
    """
    >>> from pprint import pprint
    >>> pprint(_bin_to_64([1]))
    1
    >>> pprint(_bin_to_64([2, 3]))
    533
    """
    return sum(b * 265**i for i, b in enumerate(bin_[::-1]))


def _line_to_interface(line: Iterable[Union[str, Sequence[int]]]) -> interfaces.Interface:
    """
    >>> from pprint import pprint
    >>> pprint(_line_to_interface([
    ... '1', '2', '4', [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0],
    ... [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], '0']))
    Interface(index='01', descr='01', alias='01', type='6', speed=0, oper_status='2', in_octets=0, in_ucast=0, in_mcast=0, in_bcast=0, in_discards=0, in_errors=0, out_octets=0, out_ucast=0, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='down', speed_as_text='', group=None, node=None, admin_status=None)
    >>> pprint(_line_to_interface([
    ... '2', '1', '3', [0, 0, 1, 146, 209, 24, 114, 84], [0, 0, 0, 0, 27, 195, 137, 220],
    ... [0, 0, 0, 0, 198, 226, 194, 153], [0, 0, 0, 0, 1, 249, 185, 120], [0, 0, 0, 0, 0, 0, 0, 0],
    ... '0']))
    Interface(index='02', descr='02', alias='02', type='6', speed=2000000000, oper_status='1', in_octets=2064761100, in_ucast=36144795, in_mcast=0, in_bcast=0, in_discards=0, in_errors=0, out_octets=8123033736776, out_ucast=3700628163, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)
    >>> pprint(_line_to_interface([
    ... '32', '1', '3', [0, 0, 0, 53, 6, 92, 201, 237], [0, 0, 0, 0, 222, 78, 147, 38],
    ... [0, 0, 0, 0, 26, 119, 228, 49], [0, 0, 0, 0, 1, 26, 227, 84], [0, 0, 0, 0, 0, 0, 0, 0],
    ... '0']))
    Interface(index='32', descr='32', alias='32', type='6', speed=2000000000, oper_status='1', in_octets=16547413172, in_ucast=20495714, in_mcast=0, in_bcast=0, in_discards=0, in_errors=0, out_octets=1045961420308, out_ucast=492267494, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)
    """
    index, opStatus, speed, txWords64, rxWords64, txFrames64, rxFrames64, c3Discards64, crcs = line
    index = "%02d" % int(str(index))
    return interfaces.Interface(
        index=index,
        descr=index,
        alias=index,
        type='6',
        speed=mcdata_fcport_speedbits.get(str(speed), 0),
        oper_status=mcdata_fcport_opstatus.get(str(opStatus), 'unknown'),
        in_octets=_bin_to_64(rxWords64) * 4,
        in_ucast=_bin_to_64(rxFrames64),
        in_errors=int(str(crcs)),
        out_octets=_bin_to_64(txWords64) * 4,
        out_ucast=_bin_to_64(txFrames64),
        out_discards=_bin_to_64(c3Discards64),
    )


def parse_mcdata_fcport(string_table: type_defs.SNMPStringByteTable) -> interfaces.Section:
    return [_line_to_interface(line) for line in string_table[0]]


register.snmp_section(
    name="mcdata_fcport",
    parse_function=parse_mcdata_fcport,
    trees=[
        SNMPTree(
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
    ],
    # check if number of network interfaces (IF-MIB::ifNumber.0) is at least 2
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.289."),
)

register.check_plugin(
    name="mcdata_fcport",
    service_name="Port %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type="all",
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=interfaces.discover_interfaces,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=if64.generic_check_if64,
    cluster_check_function=interfaces.cluster_check,
)
