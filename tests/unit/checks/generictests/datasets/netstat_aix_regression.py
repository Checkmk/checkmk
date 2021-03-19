#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'netstat'


info = [[u'tcp4', u'0', u'0', u'127.0.0.1.32832', u'127.0.0.1.32833', u'ESTABLISHED'],
        [u'tcp',
         u'0',
         u'0',
         u'172.22.182.179.45307',
         u'172.22.182.179.3624',
         u'ESTABLISHED']]


discovery = {'': []}

checks = {'': [("connections", {}, [(0, "Matching entries found: 2", [("connections", 2)]) ])]}
