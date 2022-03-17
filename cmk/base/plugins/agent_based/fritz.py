#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence
from .agent_based_api.v1 import register, type_defs
from .utils import interfaces

Section = Mapping[str, str]


def parse_fritz(string_table: type_defs.StringTable) -> Section:
    return {line[0]: ' '.join(line[1:]) for line in string_table if len(line) > 1}


register.agent_section(
    name="fritz",
    parse_function=parse_fritz,
)


#
# WAN Interface Check
#
def _section_to_interface(section: Section) -> interfaces.Section:
    link_stat = section.get('NewLinkStatus')
    if not link_stat:
        oper_status = '4'
    elif link_stat == 'Up':
        oper_status = '1'
    else:
        oper_status = '2'
    return [
        interfaces.Interface(
            index='0',
            descr='WAN',
            alias='WAN',
            type='6',
            speed=int(section.get('NewLayer1DownstreamMaxBitRate', 0)),
            oper_status=oper_status,
            in_octets=int(section.get('NewTotalBytesReceived', 0)),
            out_octets=int(section.get('NewTotalBytesSent', 0)),
        )
    ]


def discover_fritz_wan_if(
    params: Sequence[Mapping[str, Any]],
    section: Section,
) -> type_defs.DiscoveryResult:
    yield from interfaces.discover_interfaces(
        params,
        _section_to_interface(section),
    )


def check_fritz_wan_if(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> type_defs.CheckResult:
    params_updated = dict(params)
    params_updated.update({
        'assumed_speed_in': int(section['NewLayer1DownstreamMaxBitRate']),
        'assumed_speed_out': int(section['NewLayer1UpstreamMaxBitRate']),
        'unit': 'bit',
    })
    yield from interfaces.check_multiple_interfaces(
        item,
        params_updated,
        _section_to_interface(section),
    )


register.check_plugin(
    name="fritz_wan_if",
    sections=["fritz"],
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_fritz_wan_if,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_fritz_wan_if,
)
