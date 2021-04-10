#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'quantum_libsmall_status'

info = [[],
        [[u'1.0', u'1'], [u'2.0', u'1'], [u'3.0', u'1'], [u'4.0', u'1'], [u'5.0', u'1'],
         [u'6.0', u'1'], [u'7.0', u'1'], [u'8.0', u'2']]]

discovery = {'': [(None, None)]}

checks = {
    '': [(None, {}, [(0, 'Power: good', []), (0, 'Cooling: good', []), (0, 'Control: good', []),
                     (0, 'Connectivity: good', []), (0, 'Robotics: good', []), (0, 'Media: good',
                                                                                []),
                     (0, 'Drive: good', []), (0, 'Operator action request: no', [])])]
}
