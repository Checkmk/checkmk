#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'ibm_svc_array'


info = [[u'27',
         u'SSD_mdisk27',
         u'online',
         u'1',
         u'POOL_0_V7000_RZ',
         u'372.1GB',
         u'online',
         u'raid1',
         u'1',
         u'256',
         u'generic_ssd'],
        [u'28',
         u'SSD_mdisk28',
         u'online',
         u'2',
         u'POOL_1_V7000_BRZ',
         u'372.1GB',
         u'online',
         u'raid1',
         u'1',
         u'256',
         u'generic_ssd'],
        [u'29',
         u'SSD_mdisk0',
         u'online',
         u'1',
         u'POOL_0_V7000_RZ',
         u'372.1GB',
         u'online',
         u'raid1',
         u'1',
         u'256',
         u'generic_ssd'],
        [u'30',
         u'SSD_mdisk1',
         u'online',
         u'2',
         u'POOL_1_V7000_BRZ',
         u'372.1GB',
         u'online',
         u'raid1',
         u'1',
         u'256',
         u'generic_ssd']]


discovery = {'': [(u'27', {}), (u'28', {}), (u'29', {}), (u'30', {})]}


checks = {'': [(u'27',
                {},
                [(0, u'Status: online, RAID Level: raid1, Tier: generic_ssd', [])]),
               (u'28',
                {},
                [(0, u'Status: online, RAID Level: raid1, Tier: generic_ssd', [])]),
               (u'29',
                {},
                [(0, u'Status: online, RAID Level: raid1, Tier: generic_ssd', [])]),
               (u'30',
                {},
                [(0, u'Status: online, RAID Level: raid1, Tier: generic_ssd', [])])]}
