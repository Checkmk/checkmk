#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.apc_rackpdu_power import parse_apc_rackpdu_power

checkname = 'apc_rackpdu_power'

parsed = parse_apc_rackpdu_power(
    [[[u'luz0010x', u'0']],
     [[u'3']],
     [[u'0', u'1', u'1', u'0'], [u'0', u'1', u'2', u'0'], [u'0', u'1', u'3', u'0']]],
)

discovery = {'': [(u'Device luz0010x', {}),
                  (u'Phase 1', {}),
                  (u'Phase 2', {}),
                  (u'Phase 3', {})]}

checks = {'': [(u'Device luz0010x',
                {},
                [(0, 'Power: 0.0 W', [('power', 0.0, None, None, None, None)])]),
               (u'Phase 1',
                {},
                [(0, 'Current: 0.0 A', [('current', 0.0, None, None, None, None)]),
                 (0, 'load normal', [])]),
               (u'Phase 2',
                {},
                [(0, 'Current: 0.0 A', [('current', 0.0, None, None, None, None)]),
                 (0, 'load normal', [])]),
               (u'Phase 3',
                {},
                [(0, 'Current: 0.0 A', [('current', 0.0, None, None, None, None)]),
                 (0, 'load normal', [])])]}
