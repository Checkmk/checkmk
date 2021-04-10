#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'md'


info = [[u'Personalities', u':', u'[linear]', u'[raid0]', u'[raid1]'],
        [u'md1', u':', u'active', u'linear', u'sda3[0]', u'sdb3[1]'],
        [u'491026496', u'blocks', u'64k', u'rounding'],
        [u'md0', u':', u'active', u'raid0', u'sda2[0]', u'sdb2[1]'],
        [u'2925532672', u'blocks', u'64k', u'chunks'],
        [u'unused', u'devices:', u'<none>']]


discovery = {'': [(u'md1', None)]}


checks = {'': [(u'md1',
                {},
                [(0, u'Status: active', []),
                 (0, 'Spare: 0, Failed: 0, Active: 2', [])])]}
