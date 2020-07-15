#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'akcp_sensor_humidity'


info = [[u'Humidity1 Description', u'', u'7', u'1'],
        [u'Humidity2 Description', u'', u'0', u'2']]


discovery = {'': [(u'Humidity1 Description', 'akcp_humidity_defaultlevels')]}


checks = {'': [(u'Humidity1 Description',
                (30, 35, 60, 65),
                [(2, 'State: sensor error', [])])]}
