#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'ceph_status'

info = [
    ['{'], ['"health":', '{'], ['"status":', '"HEALTH_OK",'],
    ['"checks":', '{},'], ['"mutes":', '[]'], ['},'],
    ['"election_epoch":', '175986,'], ['"mgrmap":', '{'],
    ['"available":', 'true,'], ['"num_standbys":', '3,'], ['"modules":', '['],
    ['"dashboard",'], ['"diskprediction_local",'], ['"restful",'],
    ['"status"'], ['],'], ['"services":', '{'],
    ['"dashboard":', '"http://gcd-virthost4.ad.gcd.de:8080/"'], ['}'], ['},'],
    ['"progress_events":', '{}'], ['}']
]

discovery = {'': [(None, {})], 'osds': [], 'pgs': [], 'mgrs': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'epoch': (1, 3, 30)
            }, [
                (0, 'Health: OK', []),
                (0, 'Epoch rate (30 minutes 0 seconds average): 0.00', [])
            ]
        )
    ],
    'mgrs': [(None, {
        'epoch': (1, 2, 5)
    }, [])]
}
