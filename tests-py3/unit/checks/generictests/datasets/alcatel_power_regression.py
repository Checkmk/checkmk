#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'alcatel_power'


info = [[u'1', u'1', u'0'],
        [u'2', u'1', u'1'],
        [u'3', u'1', u''],
        [u'4', u'1', u'0'],
        [u'5', u'1', u'1'],
        [u'6', u'1', u''],
        [u'7', u'2', u'0'],
        [u'8', u'2', u'1'],
        [u'9', u'2', u''],
        [u'10', u'2', u'0'],
        [u'11', u'2', u'1'],
        [u'12', u'2', u'']]


discovery = {'': [(u'11', {}), (u'2', {}), (u'5', {}), (u'8', {})]}


checks = {'': [(u'11', {}, [(2, '[AC] Operational status: down', [])]),
               (u'2', {}, [(0, '[AC] Operational status: up', [])]),
               (u'5', {}, [(0, '[AC] Operational status: up', [])]),
               (u'8', {}, [(2, '[AC] Operational status: down', [])])]}
