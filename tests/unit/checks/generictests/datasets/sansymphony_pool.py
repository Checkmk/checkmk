#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'sansymphony_pool'


info = [['Disk_pool_1', '57', 'Running', 'ReadWrite', 'Dynamic']]


discovery = {'': [('Disk_pool_1', 'sansymphony_pool_default_values')]}


checks = {'': [('Disk_pool_1',
                (80, 90),
                [(0,
                  'Dynamic pool Disk_pool_1 is running, its cache is in ReadWrite mode',
                  []),
                 (0,
                  'Pool allocation: 57%',
                  [('pool_allocation', 57, 80, 90, None, None)])])]}
