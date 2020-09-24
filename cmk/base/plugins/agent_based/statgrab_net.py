#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict
from .agent_based_api.v1 import (
    register,
    type_defs,
)
from .utils import if64, interfaces


def parse_statgrab_net(string_table: type_defs.AgentStringTable) -> interfaces.Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_statgrab_net([
    ... ['lo0.duplex', 'unknown'], ['lo0.interface_name', 'lo0'], ['lo0.speed', '0'],
    ... ['lo0.up', 'true'], ['mac.collisions', '0'], ['mac.collisions', '0'],
    ... ['mac.collisions', '0'], ['mac.collisions', '0'], ['mac.ierrors', '0'],
    ... ['mac.ierrors', '0'], ['mac.ierrors', '0'], ['mac.ierrors', '0'],
    ... ['mac.interface_name', 'mac'], ['mac.interface_name', 'mac'],
    ... ['mac.interface_name', 'mac'], ['mac.interface_name', 'mac'],
    ... ['mac.ipackets', '1268296097'], ['mac.ipackets', '38927952'],
    ... ['mac.ipackets', '565577805'], ['mac.ipackets', '50729410'], ['mac.oerrors', '0'],
    ... ['mac.oerrors', '0'], ['mac.oerrors', '0'], ['mac.oerrors', '0'],
    ... ['mac.opackets', '565866338'], ['mac.opackets', '8035845'],
    ... ['mac.opackets', '13022050069'], ['mac.opackets', '102'], ['mac.rx', '8539777403'],
    ... ['mac.rx', '9040025900'], ['mac.rx', '144543115933'], ['mac.rx', '125659024941'],
    ... ['mac.systime', '1413287036'], ['mac.systime', '1413287036'], ['mac.systime', '1413287036'],
    ... ['mac.systime', '1413287036'], ['mac.tx', '15206'], ['mac.tx', '19679032546569'],
    ... ['mac.tx', '124614022405'], ['mac.tx', '482272878'], ['vnet0.collisions', '0'],
    ... ['vnet0.duplex', 'unknown'], ['vnet0.ierrors', '0'], ['vnet0.interface_name', 'vnet0'],
    ... ['vnet0.ipackets', '1268296097'], ['vnet0.oerrors', '0'], ['vnet0.opackets', '13022050069'],
    ... ['vnet0.rx', '125659024941'], ['vnet0.speed', '0'], ['vnet0.systime', '1413287036'],
    ... ['vnet0.tx', '19679032546569'], ['vnet0.up', 'true'],
    ... ]))
    [Interface(index='1', descr='lo0', alias='lo0', type='24', speed=0, oper_status='1', in_octets=0, in_ucast=0, in_mcast=0, in_bcast=0, in_discards=0, in_errors=0, out_octets=0, out_ucast=0, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None),
     Interface(index='2', descr='mac', alias='mac', type='6', speed=0, oper_status='2', in_octets=125659024941, in_ucast=50729410, in_mcast=0, in_bcast=0, in_discards=0, in_errors=0, out_octets=482272878, out_ucast=102, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='down', speed_as_text='', group=None, node=None, admin_status=None),
     Interface(index='3', descr='vnet0', alias='vnet0', type='6', speed=0, oper_status='1', in_octets=125659024941, in_ucast=1268296097, in_mcast=0, in_bcast=0, in_discards=0, in_errors=0, out_octets=19679032546569, out_ucast=13022050069, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)]
    """
    nics: Dict[str, Dict[str, str]] = {}
    for nic_varname, value in string_table:
        nic_id, varname = nic_varname.split(".")
        nics.setdefault(nic_id, {})[varname] = value

    return [
        interfaces.Interface(
            index=str(nr + 1),
            descr=nic_id,
            alias=nic.get("interface_name", nic_id),
            type=nic_id.startswith("lo") and '24' or '6',
            speed=int(nic.get("speed", 0)) * 1000000,
            oper_status=nic.get("up") == 'true' and '1' or '2',
            in_octets=interfaces.saveint(nic.get("rx", 0)),
            in_ucast=interfaces.saveint(nic.get("ipackets", 0)),
            in_errors=interfaces.saveint(nic.get("ierrors", 0)),
            out_octets=interfaces.saveint(nic.get("tx", 0)),
            out_ucast=interfaces.saveint(nic.get("opackets", 0)),
            out_discards=interfaces.saveint(nic.get("collisions", 0)),
            out_errors=interfaces.saveint(nic.get("oerrors", 0)),
        ) for nr, (nic_id, nic) in enumerate(nics.items())
    ]


register.agent_section(
    name='statgrab_net',
    parse_function=parse_statgrab_net,
)

register.check_plugin(
    name="statgrab_net",
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
