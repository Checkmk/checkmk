#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'poseidon_temp'

info = [[u'Bezeichnung Sensor 1', u'1', u'16.8 C']]

discovery = {'': [(u'Bezeichnung Sensor 1', {})]}

checks = {
    '': [(u'Bezeichnung Sensor 1', {}, [
        (0, u'Sensor Bezeichnung Sensor 1, State normal', []),
        (0, u'16.8 \xb0C', [('temp', 16.8, None, None, None, None)]),
    ])]
}
