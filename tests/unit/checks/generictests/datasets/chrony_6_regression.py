#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'chrony'


info = [[u'506', u'Cannot', u'talk', u'to', u'daemon']]


extra_sections = {'': [[['I am truish']]]}


discovery = {'': []}


checks = {'': [(None,
                {'alert_delay': (300, 3600), 'ntp_levels': (10, 200.0, 500.0)},
                [(2, u'506 Cannot talk to daemon', [])])]}
