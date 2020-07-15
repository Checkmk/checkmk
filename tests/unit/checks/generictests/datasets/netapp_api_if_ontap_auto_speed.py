#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'netapp_api_if'

info = [
    [
        'interface cluster_mgmt', 'comment -', 'is-vip false',
        'address 111.222.333.444', 'dns-domain-name none',
        'is-auto-revert false',
        'lif-uuid 000-000-000',
        'firewall-policy mgmt', 'vserver peknasc01', 'role cluster_mgmt',
        'netmask-length 23', 'data-protocols.data-protocol none',
        'operational-status up', 'ipspace Default', 'netmask 255.255.254.0',
        'failover-policy broadcast_domain_wide', 'home-node myhome',
        'use-failover-group unused', 'address-family ipv4', 'current-port e0a',
        'current-node mynode', 'service-policy custom-management-14861',
        'listen-for-dns-query false',
        'service-names.lif-service-name management_portmap',
        'administrative-status up', 'failover-group Default', 'home-port e0a',
        'is-home true', 'operational-speed auto', 'send_data 0',
        'send_errors 0', 'link-status up', 'recv_errors 0', 'send_packet 0',
        'recv_packet 0', 'instance_name cluster_mgmt', 'recv_data 0'
    ],
]

discovery = {
    '': [
        ('1', "{'state': ['1'], 'speed': 0}"),
    ]
}

checks = {
    '': [
        (
            '1', {
                'errors': (0.01, 0.1),
                'state': ['1'],
                'speed': 0
            }, [
                (0, '[cluster_mgmt] (up) speed auto', []),
                (0, 'Current Port: e0a (is home port)', [])
            ]
        ),
    ]
}
