#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'ibm_svc_enclosure'


info = [[u'0',
         u'online',
         u'control',
         u'9843-AE2',
         u'6860407',
         u'2',
         u'2',
         u'2',
         u'12']]


discovery = {'': [(u'0', {})]}


checks = {'': [(u'0',
                {},
                [(0, u'Status: online', []),
                 (0, u'Online canisters: 2 of 2', []),
                 (0, u'Online PSUs: 2', [])])]}
