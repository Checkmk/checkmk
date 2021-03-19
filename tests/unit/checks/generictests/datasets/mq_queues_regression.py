#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'mq_queues'


info = [[u'[[Queue_App1_App2]]'], [u'1', u'2', u'3', u'4']]


discovery = {'': [(u'Queue_App1_App2', {})]}


checks = {'': [(u'Queue_App1_App2',
                {'consumerCount': (None, None), 'size': (None, None)},
                [(0,
                  'Queue Size: 1, Enqueue Count: 3, Dequeue Count: 4',
                  [('queue', 1, None, None, None, None),
                   ('enque', 3, None, None, None, None),
                   ('deque', 4, None, None, None, None)])])]}
