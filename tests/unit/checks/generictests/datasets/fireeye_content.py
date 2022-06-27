#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'fireeye_content'


info = [['456.180', '1', '2016/02/26 15:42:06']]

freeze_time = '2017-07-16T08:21:00'

discovery = {'': [(None, {})]}


checks = {'': [(None,
                {},
                [(0, 'Last update: 2016/02/26 15:42:06', []),
                 (0, 'Age: 1 year 140 days', []),
                 (0, 'Security version: 456.180', [])])]}
