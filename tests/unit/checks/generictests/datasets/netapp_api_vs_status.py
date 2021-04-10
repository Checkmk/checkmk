#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'netapp_api_vs_status'


info = [['kermit1_ng-mc', 'state', 'running', 'vserver-subtype', 'default'],
        ['kermit2_ng-mc', 'state', 'stopped', 'vserver-subtype', 'default'],
        ['kermit3_ng-mc', 'state', 'running', 'vserver-subtype', 'dp_destination'],
        ['kermit4_ng-mc', 'state', 'stopped', 'vserver-subtype', 'dp_destination'],
        ['kermit5_ng-mc'],
        ['kermit6_ng-mc', 'running']]


discovery = {'': [('kermit1_ng-mc', {}),
                  ('kermit2_ng-mc', {}),
                  ('kermit3_ng-mc', {}),
                  ('kermit4_ng-mc', {}),
                  ('kermit6_ng-mc', {})]}


checks = {'': [('kermit1_ng-mc',
                {},
                [(0, 'State: running', []), (0, 'Subtype: default', [])]),
               ('kermit2_ng-mc',
                {},
                [(2, 'State: stopped', []), (0, 'Subtype: default', [])]),
               ('kermit3_ng-mc',
                {},
                [(0, 'State: running', []), (0, 'Subtype: dp_destination', [])]),
               ('kermit4_ng-mc',
                {},
                [(0, 'State: stopped', []), (0, 'Subtype: dp_destination', [])]),
               ('kermit6_ng-mc', {}, [(0, 'State: running', [])])]}
