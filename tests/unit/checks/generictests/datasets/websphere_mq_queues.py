#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'websphere_mq_queues'


freeze_time = '2016-04-08 16:31:43'


mock_item_state = {'': 1460125903.0}


info = [['0', 'BRK.REPLY.CONVERTQ', '2016_04_08-16_31_43'],
        ['0',
         'BRK.REPLY.CONVERTQ',
         '5000',
         'CURDEPTH(1000)LGETDATE()LGETTIME()',
         '2016_04_08-16_31_43'],
        ['1000',
         'DEAD.QUEUE.SECURITY',
         '100000',
         'CURDEPTH(0)LGETDATE(2016-04-08)LGETTIME(15.31.43)',
         '2016_04_08-16_31_43'],
        ['2000',
         'DEAD.QUEUE.SECURITY2',
         '200000',
         'CURDEPTH(0)LGETDATE(2016-04-08)LGETTIME(15.31.43)',
         'foobar']]


discovery = {'': [('BRK.REPLY.CONVERTQ', 'websphere_mq_queues_default_levels'),
                  ('DEAD.QUEUE.SECURITY', 'websphere_mq_queues_default_levels'),
                  ('DEAD.QUEUE.SECURITY2', 'websphere_mq_queues_default_levels')]}


checks = {'': [('BRK.REPLY.CONVERTQ',
                {'message_count': (1000, 1200), 'message_count_perc': (80.0, 90.0)},
                [(0,
                  'Messages in queue: 0',
                  [('queue', 0, 1000, 1200, None, None)]),
                 (0, 'Of max. 5000 messages: 0%', []),
                 (0, 'Messages processed', [])]),
               ('DEAD.QUEUE.SECURITY',
                {'message_count': (1000, 1200), 'message_count_perc': (80.0, 90.0)},
                [(1,
                  'Messages in queue: 1000 (warn/crit at 1000/1200)',
                  [('queue', 1000, 1000, 1200, None, None)]),
                 (0, 'Of max. 100000 messages: 1.0%', []),
                 (0, 'Messages not processed since 1 hour 0 minutes', [])]),
               ('DEAD.QUEUE.SECURITY2',
                {'message_count': (1000, 1200), 'message_count_perc': (80.0, 90.0)},
                [(2,
                  'Messages in queue: 2000 (warn/crit at 1000/1200)',
                  [('queue', 2000, 1000, 1200, None, None)]),
                 (0, 'Of max. 200000 messages: 1.0%', [])])]}
