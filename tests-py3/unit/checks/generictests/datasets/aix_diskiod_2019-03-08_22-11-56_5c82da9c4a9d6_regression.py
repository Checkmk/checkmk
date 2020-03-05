#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'aix_diskiod'


info = [[None, u'hdisk0', u'5.1', u'675.7', u'46.5', u'2380130842', u'12130437130'],
        [None, u'hdisk0000', u'58.5', u'19545.1', u'557.3', u'%l', u'%l']]


discovery = {'': [('SUMMARY', 'diskstat_default_levels')]}


checks = {'': [('SUMMARY',
                {},
                [(0,
                  'read: 0.00 B/s, write: 0.00 B/s',
                  [('read', 0.0, None, None, None, None),
                   ('write', 0.0, None, None, None, None)])])]}
