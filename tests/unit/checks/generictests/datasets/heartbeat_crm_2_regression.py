#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'heartbeat_crm'

freeze_time = '2020-09-08 10:36:36'

info = [
    ['Cluster', 'Summary:'], ['_*', 'Stack:', 'corosync'],
    [
        '_*', 'Current', 'DC:', 'ha02', '(version',
        '2.0.3-5.el8_2.1-4b1f869f0f)', '-', 'partition', 'with', 'quorum'
    ], ['_*', 'Last', 'updated:', 'Tue', 'Sep', '8', '10:36:12', '2020'],
    [
        '_*', 'Last', 'change:', 'Mon', 'Sep', '7', '22:33:23', '2020', 'by',
        'root', 'via', 'cibadmin', 'on', 'ha01'
    ], ['_*', '2', 'nodes', 'configured'],
    ['_*', '3', 'resource', 'instances', 'configured'], ['Node', 'List:'],
    ['_*', 'Online:', '[', 'ha01', 'ha02', ']'],
    ['Full', 'List', 'of', 'Resources:'],
    ['_*', 'vip', '(ocf::heartbeat:IPaddr):', 'Started', 'ha01'],
    ['_*', 'Clone', 'Set:', 'splunk-clone', '[splunk]:'],
    ['_', '*', 'Started:', '[', 'ha01', 'ha02', ']']
]

discovery = {
    '': [(None, {
        'num_nodes': 2,
        'num_resources': 3
    })],
    'resources': []
}

checks = {
    '': [
        (
            None, {
                'max_age': 60,
                'num_nodes': 2,
                'num_resources': 3
            }, [
                (0, 'DC: ha02, Nodes: 2, Resources: 3', []),
            ]
        )
    ]
}
