#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'cisco_temperature'


parsed = {'8': {u'Chassis 1': {'dev_state': (3, 'sensor defect'),
                               'raw_dev_state': u'1'}}}


discovery = {'': [(u'Chassis 1', {})], 'dom': []}


checks = {'': [(u'Chassis 1', {}, [(3, 'Status: sensor defect', [])])]}
