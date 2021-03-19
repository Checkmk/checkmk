#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'netstat'


info = [[u'tcp', u'0', u'0', u'0.0.0.0:111', u'0.0.0.0:*', u'LISTENING'],
        [u'tcp',
         u'0',
         u'0',
         u'172.17.40.64:58821',
         u'172.17.1.190:8360',
         u'ESTABLISHED'],
        [u'tcp',
         u'0',
         u'0',
         u'172.17.40.64:6556',
         u'172.17.40.64:36577',
         u'TIME_WAIT'],
        [u'udp', u'0', u'0', u'fe80::250:56ff:fea2:123', u':::*']]


discovery = {'': []}

checks = {'': [("connections", {}, [(0, "Matching entries found: 4", [("connections", 4)]) ])]}
