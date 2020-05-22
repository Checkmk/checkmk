#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.cisco_vpn_sessions import parse_cisco_vpn_sessions

checkname = 'cisco_vpn_sessions'

parsed = parse_cisco_vpn_sessions([[['31', '776', '0']]])

discovery = {'': [('IPsec', {}),
                  ('SVC', {}),
                  ('WebVPN', {})]}

checks = {'': [('IPsec',
                {'active_sessions': (10, 100)},
                [(1,
                  '31 (warn/crit at 10/100)',
                  [('active_sessions', 31, 10.0, 100.0)])]),
               ('SVC',
                {'active_sessions': (10, 100)},
                [(2,
                  '776 (warn/crit at 10/100)',
                  [('active_sessions', 776, 10.0, 100.0)])]),
               ('WebVPN',
                {},
                [(0,
                  '0',
                  [('active_sessions', 0, None, None)])])]}
