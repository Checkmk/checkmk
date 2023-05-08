#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'poseidon_inputs'

info = [[u'1', u'Bezeichnung Eingang 1', u'1', u'0'], [u'0', u'Bezeichnung Eingang 2', u'2', u'0'],
        [u'0', u'Bezeichnung Eingang 3', u'1', u'1'], [u'0', u'Bezeichnung Eingang 4', u'1', u'1'],
        [u'0', u'Comm Monitor 1', u'0', u'0']]

discovery = {
    '': [(u'Bezeichnung Eingang 1', {}), (u'Bezeichnung Eingang 2', {}),
         (u'Bezeichnung Eingang 3', {}), (u'Bezeichnung Eingang 4', {}), (u'Comm Monitor 1', {})]
}

checks = {
    '': [(u'Bezeichnung Eingang 1', {}, [(0, u'Bezeichnung Eingang 1: AlarmSetup: activeOff', []),
                                         (0, 'Alarm State: normal', []), (0, 'Values on', [])]),
         (u'Bezeichnung Eingang 2', {}, [(0, u'Bezeichnung Eingang 2: AlarmSetup: activeOn', []),
                                         (0, 'Alarm State: normal', []), (0, 'Values off', [])]),
         (u'Bezeichnung Eingang 3', {}, [(0, u'Bezeichnung Eingang 3: AlarmSetup: activeOff', []),
                                         (2, 'Alarm State: alarm', []), (0, 'Values off', [])]),
         (u'Bezeichnung Eingang 4', {}, [(0, u'Bezeichnung Eingang 4: AlarmSetup: activeOff', []),
                                         (2, 'Alarm State: alarm', []), (0, 'Values off', [])]),
         (u'Comm Monitor 1', {}, [(0, u'Comm Monitor 1: AlarmSetup: inactive', []),
                                  (0, 'Alarm State: normal', []), (0, 'Values off', [])])]
}
