#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'splunk_health'


info = [[u'Overall_state', u'green'],
        [u'File_monitor_input', u'green'],
        [u'File_monitor_input', u'Tailreader-0', u'green'],
        [u'File_monitor_input', u'Batchreader-0', u'green'],
        [u'Index_processor', u'green'],
        [u'Index_processor', u'Index_optimization', u'green'],
        [u'Index_processor', u'Buckets', u'green'],
        [u'Index_processor', u'Disk_space', u'green']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'green': 0, 'red': 2, 'yellow': 1},
                [(0, u'Overall state: green', []),
                 (0, u'File monitor input: green', []),
                 (0, u'Index processor: green', []),
                 (0, u'\nBatchreader-0 - State: green\nTailreader-0 - State: green\nBuckets - State: green\nDisk space - State: green\nIndex optimization - State: green\n',
                  [])])]}
