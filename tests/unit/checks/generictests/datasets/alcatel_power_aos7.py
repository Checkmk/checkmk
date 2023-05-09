#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'alcatel_power_aos7'


info = [[u'1', u'1', u'1'],
        [u'2', u'2', u'1'],
        [u'3', u'3', u'1'],
        [u'4', u'4', u'1'],
        [u'5', u'5', u'0'],
        [u'6', u'6', u'0'],
        [u'7', u'7', u'0'],
        [u'8', u'8', u'2'],
        [u'9', u'9', u'2'],
        [u'10', u'10', u'2']]


discovery = {'': [(u'1', {}),
                  (u'10', {}),
                  (u'2', {}),
                  (u'3', {}),
                  (u'4', {}),
                  (u'8', {}),
                  (u'9', {})]}


checks = {'': [(u'1', {}, [(0, '[AC] Status: up', [])]),
               (u'10', {}, [(2, '[DC] Status: power save', [])]),
               (u'2', {}, [(2, '[AC] Status: down', [])]),
               (u'3', {}, [(2, '[AC] Status: testing', [])]),
               (u'4', {}, [(2, '[AC] Status: unknown', [])]),
               (u'8', {}, [(2, '[DC] Status: master', [])]),
               (u'9', {}, [(2, '[DC] Status: idle', [])])]}
