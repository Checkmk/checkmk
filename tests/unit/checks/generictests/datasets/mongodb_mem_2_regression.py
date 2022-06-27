#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'mongodb_mem'


info = [[u'resident', u'79'],
        [u'supported', u'True'],
        [u'virtual', u'1021'],
        [u'mappedWithJournal', u'0'],
        [u'mapped', u'0'],
        [u'bits', u'64'],
        [u'note', u'fields', u'vary', u'by', u'platform'],
        [u'page_faults', u'9']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {},
                [(0,
                  'Resident usage: 79.0 MiB',
                  [('process_resident_size', 82837504, None, None, None, None)]),
                 (0,
                  'Virtual usage: 1021 MiB',
                  [('process_virtual_size', 1070596096, None, None, None, None)]),
                 (0,
                  'Mapped usage: 0 B',
                  [('process_mapped_size', 0, None, None, None, None)])])]}
