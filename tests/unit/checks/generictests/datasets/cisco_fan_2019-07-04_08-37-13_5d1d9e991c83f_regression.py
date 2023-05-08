#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'cisco_fan'


info = [[u'Fan_1_rpm', u'', u'0'],
        [u'Fan_2_rpm', u'1', u'1'],
        [u'Fan_3_rpm', u'999', u'2']]


discovery = {'': [(u'Fan_2_rpm 1', None)]}


checks = {'': [(u'Fan_2_rpm 1', {}, [(0, u'Status: normal', [])])]}
