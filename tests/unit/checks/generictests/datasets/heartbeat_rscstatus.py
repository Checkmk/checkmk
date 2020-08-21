#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'heartbeat_rscstatus'

info = [[u'all']]

discovery = {'': [(None, {'discovered_state': u'all'})]}

checks = {
    '': [
        (None, {'discovered_state': u'all'}, [
            (0, u'Current state: all', []),
        ]),
        (None, {'discovered_state': u'local'}, [
            (2, u'Current state: all (Expected: local)', []),
        ]),
        (None, u'"all"', [
            (0, u'Current state: all', []),
        ]),
        (None, u'"local"', [
            (2, u'Current state: all (Expected: local)', []),
        ]),
    ],
}
