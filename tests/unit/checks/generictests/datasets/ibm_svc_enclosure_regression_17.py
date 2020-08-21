#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'ibm_svc_enclosure'


info = [[u'6',
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
         u'24',
         u'0',
         u'0',
         u'0',
         u'0']]


discovery = {'': [(u'6', {})]}


checks = {'': [(u'6',
                {},
                [(0, u'Status: online', []),
                 (0, u'Online canisters: 2 of 2', []),
                 (0, u'Online PSUs: 2 of 2', []),
                 (0, u'Online fan modules: 0 of 0', []),
                 (0, u'Online secondary expander modules: 0 of 0', [])])]}
