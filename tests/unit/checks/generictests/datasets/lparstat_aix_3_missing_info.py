#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'lparstat_aix'

info = [[
    u'System', u'configuration:', u'type=Shared', u'mode=Uncapped', u'smt=4', u'lcpu=8',
    u'mem=16384MB', u'psize=4', u'ent=1.00'
],
        [
            u'%user', u'%wait', u'%idle', u'physc', u'%entc', u'lbusy', u'vcsw', u'phint',
            u'%nsp', u'%utcyc'
        ],
        [
            u'-----', u'------', u'------', u'-----', u'-----', u'------', u'-----',
            u'-----', u'-----', u'------'
        ],
        [u'0.4', u'0.0', u'99.3', u'0.02', u'1.7', u'0.0', u'215', u'3', u'101', u'0.64']]

discovery = {'': [(None, {})], 'cpu_util': []}
