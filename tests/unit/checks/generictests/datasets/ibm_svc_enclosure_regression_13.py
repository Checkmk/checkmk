#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'ibm_svc_enclosure'


info = [[u'1',
         u'online',
         u'control',
         u'yes',
         u'0',
         u'io_grp0',
         u'2072-24C',
         u'7804037',
         u'2',
         u'1',
         u'2',
         u'2',
         u'24'],
        [u'2',
         u'online',
         u'expansion',
         u'yes',
         u'0',
         u'io_grp0',
         u'2072-24E',
         u'7804306',
         u'2',
         u'0',
         u'2',
         u'2',
         u'24'],
        [u'3',
         u'online',
         u'expansion',
         u'yes',
         u'0',
         u'io_grp0',
         u'2072-24E',
         u'7804326',
         u'2',
         u'1',
         u'2',
         u'2',
         u'24'],
        [u'4',
         u'online',
         u'expansion',
         u'yes',
         u'0',
         u'io_grp0',
         u'2072-24E',
         u'7804352',
         u'2',
         u'2',
         u'2',
         u'2',
         u'24']]


discovery = {'': [(u'1', {}),
                  (u'2', {}),
                  (u'3', {}),
                  (u'4', {})]}


checks = {'': [(u'1',
                {'levels_lower_online_canisters': (2, 0)},
                [(0, u'Status: online', []),
                 (1, u'Online canisters: 1 (warn/crit below 2/0) of 2', []),
                 (0, u'Online PSUs: 2 of 2', [])]),
               (u'2',
                {'levels_lower_online_canisters': (-1, -1)},
                [(0, u'Status: online', []),
                 (0, u'Online canisters: 0 of 2', []),
                 (0, u'Online PSUs: 2 of 2', [])]),
               (u'3',
                {},
                [(0, u'Status: online', []),
                 (2, u'Online canisters: 1 (warn/crit below 2/2) of 2', []),
                 (0, u'Online PSUs: 2 of 2', [])]),
               (u'4',
                {},
                [(0, u'Status: online', []),
                 (0, u'Online canisters: 2 of 2', []),
                 (0, u'Online PSUs: 2 of 2', [])])]}
