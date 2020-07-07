#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'jolokia_info'

info = [[
    'Error:', 'mk_jolokia', 'requires', 'either', 'the', 'json', 'or', 'simplejson', 'library.',
    'Please', 'either', 'use', 'a', 'Python', 'version', 'that', 'contains', 'the', 'json',
    'library', 'or', 'install', 'the', 'simplejson', 'library', 'on', 'the', 'monitored', 'system.'
], ['INSTANCE1', 'ERROR', 'HTTP404 No response from server or whatever'],
        ['INSTANCE2', 'tomcat', '3.141592', '42.23']]

discovery = {'': [('Error:', {}), ('INSTANCE1', {}), ('INSTANCE2', {})]}

checks = {
    '': [('Error:', {}, [(
        3,
        'mk_jolokia requires either the json or simplejson library. Please either use a Python version that contains the json library or install the simplejson library on the monitored system.',
        [])]), ('INSTANCE1', {}, [(2, 'ERROR HTTP404 No response from server or whatever', [])]),
         ('INSTANCE2', {}, [(0, 'Tomcat 3.141592', []), (0, 'Jolokia 42.23', [])])]
}
