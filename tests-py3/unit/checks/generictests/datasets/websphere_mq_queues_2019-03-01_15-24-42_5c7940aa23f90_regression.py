#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'websphere_mq_queues'


info = [[u'0', u'ABC-123-DEF'], [u'TEST-FOO', u'RUNNING']]


discovery = {'': [(u'ABC-123-DEF', 'websphere_mq_queues_default_levels')]}


checks = {'': [(u'ABC-123-DEF',
                {'message_count': (1000, 1200), 'message_count_perc': (80.0, 90.0)},
                [(0,
                  'Messages in queue: 0',
                  [('queue', 0, 1000.0, 1200.0, None, None)])])]}
