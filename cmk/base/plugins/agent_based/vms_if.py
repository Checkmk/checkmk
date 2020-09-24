#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import (
    register,
    type_defs,
)
from .utils import if64, interfaces


def wrap_negative(str_value: str) -> float:
    # Due to signed 32-bit arithmetics we sometimes get negative values. Those must be converted to
    # positive ones.
    c = interfaces.saveint(str_value)
    return c + 2**32 if c < 0 else c


_VMS_IF_COUNTERS_ORDER = [
    'in_octets',
    'in_ucast',
    'in_mcast',
    'in_bcast',
    'in_discards',
    'in_errors',
    'out_octets',
    'out_ucast',
    'out_mcast',
    'out_bcast',
    'out_discards',
    'out_errors',
]


def parse_vms_if(string_table: type_defs.AgentStringTable) -> interfaces.Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_vms_if([
    ... ['SE0', '0', '6680', '0', '0', '0', '0', '0', '3649', '0', '0', '0', '0'],
    ... ['WE0', '-357453266', '0', '1246887166', '0', '0'],
    ... ['WE4', '6061662', '0', '4858067', '0', '0'],
    ... ]))
    [Interface(index='1', descr='SE0', alias='SE0', type='6', speed=1000000000, oper_status='1', in_octets=0, in_ucast=6680, in_mcast=0, in_bcast=0, in_discards=0, in_errors=0, out_octets=0, out_ucast=3649, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None),
     Interface(index='2', descr='WE0', alias='WE0', type='6', speed=1000000000, oper_status='1', in_octets=3937514030, in_ucast=0, in_mcast=1246887166, in_bcast=0, in_discards=0, in_errors=0, out_octets=0, out_ucast=0, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None),
     Interface(index='3', descr='WE4', alias='WE4', type='6', speed=1000000000, oper_status='1', in_octets=6061662, in_ucast=0, in_mcast=4858067, in_bcast=0, in_discards=0, in_errors=0, out_octets=0, out_ucast=0, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)]
    """
    return [
        interfaces.Interface(
            index=str(idx + 1),
            descr=line[0],
            alias=line[0],
            type='6',  # Ethernet
            speed=1000000000,
            oper_status='1',
            **{  # type: ignore[arg-type]
                counter: wrap_negative(str_val)
                for counter, str_val in zip(_VMS_IF_COUNTERS_ORDER, line[1:])
            },
        )
        for idx, line in enumerate(string_table)
    ]


register.agent_section(
    name='vms_if',
    parse_function=parse_vms_if,
)

register.check_plugin(
    name="vms_if",
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type="all",
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=interfaces.discover_interfaces,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=if64.generic_check_if64,
    cluster_check_function=interfaces.cluster_check,
)
