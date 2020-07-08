#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'f5_bigip_pool'

info = [
    [
        ['/Common/ad_testch-pool', '2', '2'],
        ['/Common/ad_hubservice-pool', '2', '2'],
        ['/Common/ldap_testch-pool', '2', '2'],
        ['/Common/ldap_testhk-pool', '2', '2']
    ],
    [
        ['/Common/ad_testch-pool', '0', '4', '4', '1', '/Common/11.11.128.61'],
        ['/Common/ad_testch-pool', '0', '4', '4', '1', '/Common/11.11.129.61'],
        [
            '/Common/ad_hubservice-pool', '0', '4', '4', '1',
            '/Common/11.11.81.201'
        ],
        [
            '/Common/ad_hubservice-pool', '0', '4', '4', '1',
            '/Common/11.11.81.202'
        ],
        [
            '/Common/ldap_testch-pool', '389', '4', '4', '1',
            '/Common/11.11.128.61'
        ],
        [
            '/Common/ldap_testch-pool', '389', '4', '4', '1',
            '/Common/11.11.129.61'
        ],
        [
            '/Common/ldap_testhk-pool', '389', '4', '4', '1',
            '/Common/rozrhvad22.testhk.testint.net'
        ],
        [
            '/Common/ldap_testhk-pool', '389', '4', '4', '1',
            '/Common/rozrhvad23.testhk.testint.net'
        ]
    ]
]

discovery = {
    '': [
        ('/Common/ad_hubservice-pool', 'f5_bigip_pool_default_levels'),
        ('/Common/ad_testch-pool', 'f5_bigip_pool_default_levels'),
        ('/Common/ldap_testch-pool', 'f5_bigip_pool_default_levels'),
        ('/Common/ldap_testhk-pool', 'f5_bigip_pool_default_levels')
    ]
}

checks = {
    '': [
        (
            '/Common/ad_hubservice-pool', (2, 1), [
                (0, '2 of 2 members are up', [])
            ]
        ),
        ('/Common/ad_testch-pool', (2, 1), [(0, '2 of 2 members are up', [])]),
        (
            '/Common/ldap_testch-pool', (2, 1), [
                (0, '2 of 2 members are up', [])
            ]
        ),
        (
            '/Common/ldap_testhk-pool', (2, 1), [
                (0, '2 of 2 members are up', [])
            ]
        )
    ]
}
