#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.lnx_if import parse_lnx_if


@pytest.mark.parametrize('string_table, result', [
    ([
        [u'[start_iplink]'],
        [
            u'1:', u'wlp3s0:', u'<BROADCAST,MULTICAST>', u'mtu', u'1500', u'qdisc', u'fq_codel',
            u'state', u'UP', u'mode', u'DORMANT', u'group', u'default', u'qlen', u'1000'
        ],
        [u'link/ether', u'AA:AA:AA:AA:AA:AA', u'brd', u'BB:BB:BB:BB:BB:BB'],
        [u'[end_iplink]'],
        [u'wlp3s0', u'130923553 201184 0 0 0 0 0 16078 23586281 142684 0 0 0 0 0 0'],
    ], [
        [
            '1', 'wlp3s0', '6', '', '2', '130923553', '217262', '16078', '0', '0', '0', '23586281',
            '142684', '0', '0', '0', '0', '0', 'wlp3s0', '\xaa\xaa\xaa\xaa\xaa\xaa'
        ],
    ]),
    ([
        [u'[start_iplink]'],
        [
            u'1:', u'wlp3s0:', u'<BROADCAST,MULTICAST,UP>', u'mtu', u'1500', u'qdisc', u'fq_codel',
            u'state', u'UP', u'mode', u'DORMANT', u'group', u'default', u'qlen', u'1000'
        ],
        [u'link/ether', u'BB:BB:BB:BB:BB:BB', u'brd', u'BB:BB:BB:BB:BB:BB'],
        [u'[end_iplink]'],
        [u'wlp3s0', u'130923553 201184 0 0 0 0 0 16078 23586281 142684 0 0 0 0 0 0'],
    ], [
        [
            '1', 'wlp3s0', '6', '', '1', '130923553', '217262', '16078', '0', '0', '0', '23586281',
            '142684', '0', '0', '0', '0', '0', 'wlp3s0', '\xbb\xbb\xbb\xbb\xbb\xbb'
        ],
    ])
])
def test_lnx_if_status_flags(string_table, result):
    assert parse_lnx_if(string_table)[0] == result
