#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Result,
    Service,
    State as state,
    type_defs,
)
from cmk.base.plugins.agent_based import netapp_api_if
from cmk.base.plugins.agent_based.utils import interfaces


@pytest.mark.parametrize('string_table, discovery_results, items_params_results', [
    (
        [
            [
                u'interface GTB1020-2-CL_mgmt', u'comment -', u'use-failover-group unused',
                u'address 191.128.142.33', u'dns-domain-name none', u'is-auto-revert false',
                u'lif-uuid d3233231-a1d3-12e6-a4ff-00a0231e0e11', u'firewall-policy mgmt',
                u'vserver FSS2220-2-CL', u'role cluster_mgmt', u'netmask-length 24',
                u'data-protocols.data-protocol none', u'operational-status up', u'ipspace Default',
                u'netmask 255.255.254.0', u'failover-policy broadcast_domain_wide',
                u'home-node FSS2220-2', u'address-family ipv4', u'current-port e0f-112',
                u'current-node FSS2220-2', u'is-dns-update-enabled false', u'subnet-name MGMT',
                u'listen-for-dns-query false', u'administrative-status up',
                u'failover-group MGMT-Netz', u'home-port e0f-112', u'is-home true',
                u'operational-speed 1000', u'send_data 0', u'send_errors 0', u'link-status up',
                u'recv_errors 0', u'send_packet 0', u'recv_packet 0',
                u'instance_name FSS2220-2-CL_mgmt', u'recv_data 0'
            ],
            [
                u'interface GTB1020-2_ic1', u'comment -', u'use-failover-group unused',
                u'address 10.12.1.4', u'dns-domain-name none', u'is-auto-revert false',
                u'lif-uuid sdfd13d4d-82db-12c5-a2ff-00a123e0e49', u'firewall-policy intercluster',
                u'vserver FSS2220-1-DL', u'role intercluster', u'netmask-length 24',
                u'data-protocols.data-protocol none', u'operational-status up', u'ipspace Default',
                u'netmask 255.255.244.0', u'failover-policy local_only', u'home-node FSS2220-2',
                u'address-family ipv4', u'current-port e0f-1137', u'current-node FSS2220-2',
                u'listen-for-dns-query false', u'administrative-status up',
                u'failover-group Intercluster', u'home-port e0f-2231', u'is-home true',
                u'operational-speed 1000', u'send_data 142310234', u'send_errors 0',
                u'link-status up', u'recv_errors 0', u'send_packet 2223111', u'recv_packet 2223411',
                u'instance_name FSS2220_ic1', u'recv_data 122333190'
            ],
        ],
        [
            Service(
                item='1',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 1000000000,
                },
            ),
            Service(
                item='2',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 1000000000,
                },
            ),
        ],
        [
            (
                '1',
                {
                    'errors': (0.01, 0.1),
                    'discovered_speed': 1000000000,
                    'discovered_oper_status': ['1']
                },
                [
                    Result(state=state.OK, summary='[GTB1020-2-CL_mgmt]'),
                    Result(state=state.OK, summary='Operational state: up'),
                    Result(state=state.OK, summary='1 GBit/s'),
                    Result(state=state.OK, summary='Current Port: e0f-112 (is home port)'),
                ],
            ),
            (
                '2',
                {
                    'errors': (0.01, 0.1),
                    'discovered_speed': 1000000000,
                    'discovered_oper_status': ['1']
                },
                [
                    Result(state=state.OK, summary='[GTB1020-2_ic1]'),
                    Result(state=state.OK, summary='Operational state: up'),
                    Result(state=state.OK, summary='1 GBit/s'),
                    Result(state=state.OK, summary='Current Port: e0f-2231 (is home port)'),
                ],
            ),
        ],
    ),
    (
        [
            [
                u'interface e0a', u'mediatype auto-1000t-fd-up', u'flowcontrol full',
                u'mtusize 9000', u'ipspace-name default-ipspace', u'mac-address 01:b0:89:22:df:01'
            ],
            [
                u'interface e0b', u'mediatype auto-1000t-fd-up', u'flowcontrol full',
                u'mtusize 9000', u'ipspace-name default-ipspace', u'mac-address 01:b0:89:22:df:01'
            ],
            [
                u'interface e0c', u'ipspace-name default-ipspace', u'flowcontrol full',
                u'mediatype auto-1000t-fd-up', u'mac-address 01:b0:89:22:df:02'
            ],
            [
                u'interface e0d', u'ipspace-name default-ipspace', u'flowcontrol full',
                u'mediatype auto-1000t-fd-up', u'mac-address 01:b0:89:22:df:02'
            ],
            [
                u'interface ifgrp_sto', u'v4-primary-address.ip-address-info.address 11.12.121.33',
                u'v4-primary-address.ip-address-info.addr-family af-inet', u'mtusize 9000',
                u'v4-primary-address.ip-address-info.netmask-or-prefix 255.255.255.220',
                u'v4-primary-address.ip-address-info.broadcast 12.13.142.33',
                u'ipspace-name default-ipspace', u'mac-address 01:b0:89:22:df:01',
                u'v4-primary-address.ip-address-info.creator vfiler:vfiler0',
                u'send_mcasts 1360660', u'recv_errors 0', u'instance_name ifgrp_sto',
                u'send_errors 0', u'send_data 323931282332034', u'recv_mcasts 1234567',
                u'v4-primary-address.ip-address-info.address 11.12.121.21',
                u'v4-primary-address.ip-address-info.addr-family af-inet',
                u'v4-primary-address.ip-address-info.netmask-or-prefix 255.255.253.0',
                u'v4-primary-address.ip-address-info.broadcast 14.11.123.255',
                u'ipspace-name default-ipspace', u'mac-address 01:b0:89:22:df:02',
                u'v4-primary-address.ip-address-info.creator vfiler:vfiler0', u'send_mcasts 166092',
                u'recv_errors 0', u'instance_name ifgrp_srv-600', u'send_errors 0',
                u'send_data 12367443455534', u'recv_mcasts 2308439', u'recv_data 412332323639'
            ],
        ],
        [
            Service(
                item='5',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 1000000000,
                },
            ),
        ],
        [
            (
                '5',
                {
                    'errors': (0.01, 0.1),
                    'discovered_speed': 1000000000,
                    'discovered_oper_status': ['1']
                },
                [
                    Result(state=state.OK, summary='[ifgrp_sto]'),
                    Result(state=state.OK, summary='Operational state: up'),
                    Result(state=state.OK, summary='MAC: 01:B0:89:22:DF:02'),
                    Result(state=state.OK, summary='1 GBit/s'),
                    Result(state=state.OK, summary='Physical interfaces: e0c(up)'),
                    Result(state=state.OK, summary='e0d(up)'),
                ],
            ),
        ],
    ),
    (
        [
            [
                'interface cluster_mgmt', 'comment -', 'is-vip false', 'address 111.222.333.444',
                'dns-domain-name none', 'is-auto-revert false', 'lif-uuid 000-000-000',
                'firewall-policy mgmt', 'vserver peknasc01', 'role cluster_mgmt',
                'netmask-length 23', 'data-protocols.data-protocol none', 'operational-status up',
                'ipspace Default', 'netmask 255.255.254.0', 'failover-policy broadcast_domain_wide',
                'home-node myhome', 'use-failover-group unused', 'address-family ipv4',
                'current-port e0a', 'current-node mynode', 'service-policy custom-management-14861',
                'listen-for-dns-query false', 'service-names.lif-service-name management_portmap',
                'administrative-status up', 'failover-group Default', 'home-port e0a',
                'is-home true', 'operational-speed auto', 'send_data 0', 'send_errors 0',
                'link-status up', 'recv_errors 0', 'send_packet 0', 'recv_packet 0',
                'instance_name cluster_mgmt', 'recv_data 0'
            ],
        ],
        [
            Service(
                item='1',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 0,
                },
            ),
        ],
        [
            (
                '1',
                {
                    'errors': (0.01, 0.1),
                    'discovered_speed': 0,
                    'discovered_oper_status': ['1']
                },
                [
                    Result(state=state.OK, summary='[cluster_mgmt]'),
                    Result(state=state.OK, summary='Operational state: up'),
                    Result(state=state.OK, summary='speed auto'),
                    Result(state=state.OK, summary='Current Port: e0a (is home port)'),
                ],
            ),
        ],
    ),
])
def test_netapp_api_if_regression(
    monkeypatch,
    string_table,
    discovery_results,
    items_params_results,
):
    section = netapp_api_if.parse_netapp_api_if(string_table)

    assert list(
        netapp_api_if.discover_netapp_api_if(
            [type_defs.Parameters(interfaces.DISCOVERY_DEFAULT_PARAMETERS)],
            section,
        )) == discovery_results

    monkeypatch.setattr(interfaces, 'get_value_store', lambda: {})
    for item, par, res in items_params_results:
        assert list(netapp_api_if.check_netapp_api_if(
            item,
            type_defs.Parameters(par),
            section,
        )) == res
