#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.lparstat_aix import parse_lparstat_aix

checkname = 'lparstat_aix'

parsed = parse_lparstat_aix([
    ['System', 'Config', 'type=Dedicated', 'ent=7.0', 'what=ever'],
    [
        u'%user', u'%sys', u'%wait', u'%idle', u'physc', u'%entc', u'lbusy', u'vcsw', u'phint',
        u'%nsp', u'%utcyc'
    ],
    [
        u'#', u'-----', u'-----', u'------', u'------', u'-----', u'-----', u'------', u'-----',
        u'-----', u'-----', u'------'
    ],
    [u'0.2', u'0.4', u'0.0', u'99.3', u'0.02', u'1.7', u'0.0', u'215', u'3', u'101', u'0.64'],
])

discovery = {'': [(None, {})], 'cpu_util': [(None, {})]}

checks = {
    '': [(None, (5, 10), [
        (0, u'Physc: 0.02', [(u'physc', 0.02, None, None, None, None)]),
        (0, u'Entc: 1.7%', [(u'entc', 1.7, None, None, None, None)]),
        (0, u'Lbusy: 0.0', [(u'lbusy', 0.0, None, None, None, None)]),
        (0, u'Vcsw: 215.0', [(u'vcsw', 215.0, None, None, None, None)]),
        (0, u'Phint: 3.0', [(u'phint', 3.0, None, None, None, None)]),
        (0, u'Nsp: 101.0%', [(u'nsp', 101.0, None, None, None, None)]),
        (0, u'Utcyc: 0.64%', [(u'utcyc', 0.64, None, None, None, None)]),
    ]),],
    'cpu_util': [(None, None, [
        (0, 'User: 0.2%', [('user', 0.2)]),
        (0, 'System: 0.4%', [('system', 0.4)]),
        (0, 'Wait: 0%', [('wait', 0.0)]),
        (0, 'Total CPU: 0.6%', [('util', 0.6000000000000001, None, None, 0, None)]),
        (0, "Physical CPU consumption: 0.02 CPUs", [('cpu_entitlement_util', 0.02)]),
        (0, 'Entitlement: 7.00 CPUs', [('cpu_entitlement', 7.0)]),
    ]),],
}
