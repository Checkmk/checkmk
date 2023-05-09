#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'quanta_voltage'


info = [[[u'1', u'3', u'Volt_P12V', u'12240', u'12600', u'-99', u'-99', u'11400'],
         [u'2', u'3', u'Volt_P1V05', u'1058', u'1200', u'1000', u'-99', u'989'],
         [u'3', u'3', u'Volt_P1V8_AUX', u'100', u'2000', u'1000', u'-99', u'1705'],
         [u'4', u'3', u'Volt_P3V3', u'3370', u'3466', u'-99', u'-99', u'3132'],
         [u'5', u'3', u'Volt_P3V3_AUX', u'3370', u'34000', u'-99', u'4000', u'5000'],
         [u'6', u'3', u'Volt_P3V_BAT', u'3161', u'38000', u'-99', u'2000', u'1600'],
         [u'7', u'3', u'Volt_P5V', u'5009', u'5251', u'-99', u'-99', u'4743'],
         [u'17',
          u'3',
          u'Volt_SAS_EXP_3V3\x01',
          u'3302',
          u'4000',
          u'3000',
          u'-99',
          u'2958'],
         [u'18',
          u'3',
          u'Volt_SAS_EXP_VCC\x01',
          u'3276',
          u'3000',
          u'2800',
          u'-99',
          u'2964']]]


discovery = {'': [(u'Volt_P12V', {}),
                  (u'Volt_P1V05', {}),
                  (u'Volt_P1V8_AUX', {}),
                  (u'Volt_P3V3', {}),
                  (u'Volt_P3V3_AUX', {}),
                  (u'Volt_P3V_BAT', {}),
                  (u'Volt_P5V', {}),
                  (u'Volt_SAS_EXP_3V3', {}),
                  (u'Volt_SAS_EXP_VCC', {})]}


checks = {'': [(u'Volt_P12V',
                {},
                [(0, 'Status: OK', []),
                 (0,
                  '12240.00 V',
                  [('voltage', 12240.0, 12600.0, 12600.0, None, None)])]),
               (u'Volt_P1V05',
                {},
                [(0, 'Status: OK', []),
                 (1,
                  '1058.00 V (warn/crit at 1000.00 V/1200.00 V)',
                  [('voltage', 1058.0, 1000.0, 1200.0, None, None)])]),
               (u'Volt_P1V8_AUX',
                {},
                [(0, 'Status: OK', []),
                 (2,
                  '100.00 V (warn/crit below 1705.00 V/1705.00 V)',
                  [('voltage', 100.0, 1000.0, 2000.0, None, None)])]),
               (u'Volt_P3V3',
                {},
                [(0, 'Status: OK', []),
                 (0, '3370.00 V', [('voltage', 3370.0, 3466.0, 3466.0, None, None)])]),
               (u'Volt_P3V3_AUX',
                {},
                [(0, 'Status: OK', []),
                 (2,
                  '3370.00 V (warn/crit below 4000.00 V/5000.00 V)',
                  [('voltage', 3370.0, 34000.0, 34000.0, None, None)])]),
               (u'Volt_P3V_BAT',
                {},
                [(0, 'Status: OK', []),
                 (0,
                  '3161.00 V',
                  [('voltage', 3161.0, 38000.0, 38000.0, None, None)])]),
               (u'Volt_P5V',
                {},
                [(0, 'Status: OK', []),
                 (0, '5009.00 V', [('voltage', 5009.0, 5251.0, 5251.0, None, None)])]),
               (u'Volt_SAS_EXP_3V3',
                {},
                [(0, 'Status: OK', []),
                 (1,
                  '3302.00 V (warn/crit at 3000.00 V/4000.00 V)',
                  [('voltage', 3302.0, 3000.0, 4000.0, None, None)])]),
               (u'Volt_SAS_EXP_VCC',
                {},
                [(0, 'Status: OK', []),
                 (2,
                  '3276.00 V (warn/crit at 2800.00 V/3000.00 V)',
                  [('voltage', 3276.0, 2800.0, 3000.0, None, None)])])]}
