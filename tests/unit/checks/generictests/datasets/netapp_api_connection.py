#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'netapp_api_connection'

info = [['line_0_element_0', 'line_0_element_1'], ['line_1_element_0', 'line_1_element_1'],
        ['line_2_element_0', 'line_2_element_1', 'line_2_element_2']]

discovery = {'': [(None, [])]}

checks = {
    '': [(None, {}, [(
        1,
        'line_0_element_0 line_0_element_1, line_1_element_0 line_1_element_1, line_2_element_0 line_2_element_1 line_2_element_2',
        [])])]
}
