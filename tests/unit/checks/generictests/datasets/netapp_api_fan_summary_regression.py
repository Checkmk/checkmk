#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'netapp_api_fan'


info = [[u'cooling-element-list 0',
         u'cooling-element-number 1',
         u'rpm 3000',
         u'cooling-element-is-error false'],
        [u'cooling-element-list 0',
         u'cooling-element-number 2',
         u'rpm 3000',
         u'cooling-element-is-error true'],
        [u'cooling-element-list 0',
         u'cooling-element-number 3',
         u'rpm 3000',
         u'cooling-element-is-error false'],
        [u'cooling-element-list 0',
         u'cooling-element-number 4',
         u'rpm 3020',
         u'cooling-element-is-error false']]


discovery = {'': [], 'summary': [('Summary', {})]}


checks = {'summary': [('Summary',
                       {},
                       [(0, '4 fans in total', []),
                        (2, u'1 fan in error state (0/2)', [])])]}


mock_host_conf_merged = {'': {'mode': 'summarize'}, 'summary': {'mode': 'summarize'}}
