#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'quanta_fan'


info = [[[u'1', u'3', u'Fan_SYS0_1', u'1000', u'1500', u'800', u'-99', u'500'],
         [u'2', u'3', u'Fan_SYS0_2', u'1400', u'1200', u'1000', u'-99', u'500'],
         [u'4', u'3', u'Fan_SYS1_2', u'9200', u'10000', u'-99', u'-99', u'500'],
         [u'5', u'3', u'Fan_SYS2_1', u'11300', u'-99', u'-99', u'1000', u'500'],
         [u'6', u'3', u'Fan_SYS2_2', u'1400', u'-99', u'-99', u'2000', u'1000'],
         [u'7', u'3', u'Fan_SYS3_1', u'500', u'-99', u'-99', u'2000', u'1500'],
         [u'8', u'3', u'Fan_SYS3_2', u'9300', u'-99', u'-99', u'-99', u'500']]]


discovery = {'': [(u'Fan_SYS0_1', {}),
                  (u'Fan_SYS0_2', {}),
                  (u'Fan_SYS1_2', {}),
                  (u'Fan_SYS2_1', {}),
                  (u'Fan_SYS2_2', {}),
                  (u'Fan_SYS3_1', {}),
                  (u'Fan_SYS3_2', {})]}


checks = {'': [(u'Fan_SYS0_1',
                {},
                [(0, 'Status: OK', []),
                 (1, 'Speed: 1000 RPM (warn/crit at 800 RPM/1500 RPM)', [])]),
               (u'Fan_SYS0_2',
                {},
                [(0, 'Status: OK', []),
                 (2, 'Speed: 1400 RPM (warn/crit at 1000 RPM/1200 RPM)', [])]),
               (u'Fan_SYS1_2',
                {},
                [(0, 'Status: OK', []), (0, 'Speed: 9200 RPM', [])]),
               (u'Fan_SYS2_1',
                {},
                [(0, 'Status: OK', []), (0, 'Speed: 11300 RPM', [])]),
               (u'Fan_SYS2_2',
                {},
                [(0, 'Status: OK', []),
                 (1, 'Speed: 1400 RPM (warn/crit below 2000 RPM/1000 RPM)', [])]),
               (u'Fan_SYS3_1',
                {},
                [(0, 'Status: OK', []),
                 (2, 'Speed: 500 RPM (warn/crit below 2000 RPM/1500 RPM)', [])]),
               (u'Fan_SYS3_2',
                {},
                [(0, 'Status: OK', []), (0, 'Speed: 9300 RPM', [])])]}
