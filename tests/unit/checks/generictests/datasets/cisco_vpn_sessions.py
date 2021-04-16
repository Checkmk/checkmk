#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.cisco_vpn_sessions import parse_cisco_vpn_sessions

checkname = 'cisco_vpn_sessions'

parsed = parse_cisco_vpn_sessions([['31', '100', '50', '2', '55', '11', '776', '10000', '800',
                                     '0', '0', '0', '12345']])

discovery = {'': [('IPsec RA', {}),
                  ('IPsec L2L', {}),
                  ('AnyConnect SVC', {}),
                  ('WebVPN', {}),
                  ('Summary', {})]}

checks = {'': [('IPsec RA',
                {'active_sessions': (10, 100)},
                [(1,
                  'Active sessions: 31 (warn/crit at 10/100)',
                  [('active_sessions', 31, 10.0, 100.0)]),
                 (0,
                  'Peak count: 50',
                  [('active_sessions_peak', 50)]),
                 (0,
                  'Overall system maximum: 12345'),
                 (0,
                  'Cumulative count: 100')]),
               ('IPsec L2L',
                {'active_sessions': (10, 100)},
                [(0,
                  'Active sessions: 2',
                  [('active_sessions', 2, 10.0, 100.0)]),
                 (0,
                  'Peak count: 11',
                  [('active_sessions_peak', 11)]),
                 (0,
                  'Overall system maximum: 12345'),
                 (0,
                  'Cumulative count: 55')]),
               ('AnyConnect SVC',
                {'active_sessions': (10, 100)},
                [(2,
                  'Active sessions: 776 (warn/crit at 10/100)',
                  [('active_sessions', 776, 10.0, 100.0)]),
                 (0,
                  'Peak count: 800',
                  [('active_sessions_peak', 800)]),
                 (0,
                  'Overall system maximum: 12345'),
                 (0,
                  'Cumulative count: 10000')]),
               ('WebVPN',
                {},
                [(0,
                  'Active sessions: 0',
                  [('active_sessions', 0)]),
                 (0,
                  'Peak count: 0',
                  [('active_sessions_peak', 0)]),
                 (0,
                  'Overall system maximum: 12345'),
                 (0,
                  'Cumulative count: 0')]),
               ('Summary',
                {},
                [(0,
                  'Active sessions: 809',
                  [('active_sessions', 809)]),
                 (0,
                  'Overall system maximum: 12345'),
                 (0,
                  'Cumulative count: 10155')])]}
