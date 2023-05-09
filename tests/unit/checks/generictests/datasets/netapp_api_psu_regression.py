#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'netapp_api_psu'


info = [[u'power-supply-list 0',
         u'is-auto-power-reset-enabled false',
         u'power-supply-part-no 114-00065+A2',
         u'power-supply-serial-no XXT133880145',
         u'power-supply-is-error false',
         u'power-supply-firmware-revision 020F',
         u'power-supply-type 9C',
         u'power-supply-swap-count 0',
         u'power-supply-element-number 1'],
        [u'power-supply-list 0',
         u'is-auto-power-reset-enabled false',
         u'power-supply-part-no 114-00065+A2',
         u'power-supply-serial-no XXT133880140',
         u'power-supply-is-error true',
         u'power-supply-firmware-revision 020F',
         u'power-supply-type 9C',
         u'power-supply-swap-count 0',
         u'power-supply-element-number 2']]


discovery = {'': [(u'0/1', None), (u'0/2', None)], 'summary': []}


checks = {'': [(u'0/1', {}, [(0, 'Operational state OK', [])]),
               (u'0/2', {}, [(2, u'Error in PSU 2', [])])]}
