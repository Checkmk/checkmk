#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'mongodb_mem'


info = [['resident', '856'],
        ['supported', 'True'],
        ['virtual', '6100'],
        ['mappedWithJournal', '5374'],
        ['mapped', '2687'],
        ['bits', '64'],
        ['note', 'fields', 'vary', 'by', 'platform'],
        ['page_faults', '86'],
        ['heap_usage_bytes', '65501032']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {},
                [(0,
                  'Resident usage: 856 MiB',
                  [('process_resident_size', 897581056, None, None, None, None)]),
                 (0,
                  'Virtual usage: 5.96 GiB',
                  [('process_virtual_size', 6396313600, None, None, None, None)]),
                 (0,
                  'Mapped usage: 2.62 GiB',
                  [('process_mapped_size', 2817523712, None, None, None, None)])])]}
