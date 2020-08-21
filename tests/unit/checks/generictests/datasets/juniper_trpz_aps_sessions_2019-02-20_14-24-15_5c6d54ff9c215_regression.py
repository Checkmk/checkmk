#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'juniper_trpz_aps_sessions'


info = [[['foo-42-bar', u'10.48.57.101.50.49.48.48.54.50.53', u'7', u'F.oo-23-B.ar']],
        [['foo-42-bar',
          u'10.48.57.101.50.49.48.48.54.50.53.1',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0'],
         ['foo-42-bar',
          u'10.48.57.101.50.49.48.48.54.50.53.2',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0',
          u'0'],
         ['foo-42-bar',
          u'',
          u'',
          u'',
          u'',
          u'',
          u'',
          u'',
          u'',
          u'',
          u'',
          u'0',
          u'-90'],
         ['foo-42-bar',
          u'',
          u'',
          u'',
          u'',
          u'',
          u'',
          u'',
          u'',
          u'',
          u'',
          u'0',
          u'-100']]]


discovery = {'': [(u'F.oo-23-B.ar', None)]}


checks = {'': [(u'F.oo-23-B.ar',
                {},
                [(0, '[foo-42-bar] Status: operational', []),
                 (0,
                  u'Radio 1: Input: 0.00 B/s, Output: 0.00 B/s, Errors: 0, Resets: 0, Retries: 0, Sessions: 0, Noise: 0 dBm, Radio 2: Input: 0.00 B/s, Output: 0.00 B/s, Errors: 0, Resets: 0, Retries: 0, Sessions: 0, Noise: 0 dBm',
                  [('if_out_unicast', 0, None, None, None, None),
                   ('if_out_unicast_octets', 0.0, None, None, None, None),
                   ('if_out_non_unicast', 0.0, None, None, None, None),
                   ('if_out_non_unicast_octets', 0.0, None, None, None, None),
                   ('if_in_pkts', 0.0, None, None, None, None),
                   ('if_in_octets', 0.0, None, None, None, None),
                   ('wlan_physical_errors', 0.0, None, None, None, None),
                   ('wlan_resets', 0.0, None, None, None, None),
                   ('wlan_retries', 0.0, None, None, None, None),
                   ('total_sessions', 0, None, None, None, None),
                   ('noise_floor', 0, None, None, None, None)])])]}
