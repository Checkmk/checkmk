#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'fsc_fans'


info = [[u'NULL', u'NULL'], [u'FAN1 SYS', u'4140']]


discovery = {'': [(u'FAN1 SYS', {})]}


checks = {'': [(u'FAN1 SYS', {'lower': (2000, 1000)}, [(0, 'Speed: 4140 RPM', [])])]}
