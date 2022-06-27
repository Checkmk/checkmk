#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'elasticsearch_cluster_health'


info = [[u'status', u'green'],
        [u'number_of_nodes', u'5'],
        [u'unassigned_shards', u'0'],
        [u'number_of_pending_tasks', u'0'],
        [u'number_of_in_flight_fetch', u'0'],
        [u'timed_out', u'False'],
        [u'active_primary_shards', u'4'],
        [u'task_max_waiting_in_queue_millis', u'0'],
        [u'cluster_name', u'My-cluster'],
        [u'relocating_shards', u'0'],
        [u'active_shards_percent_as_number', u'100.0'],
        [u'active_shards', u'8'],
        [u'initializing_shards', u'0'],
        [u'number_of_data_nodes', u'5'],
        [u'delayed_unassigned_shards', u'0']]


discovery = {'': [(None, {})], 'shards': [(None, {})], 'tasks': [(None, {})]}


checks = {'': [(None,
                {},
                [(0, u'Name: My-cluster', []),
                 (0,
                  'Data nodes: 5',
                  [(u'number_of_data_nodes', 5, None, None, None, None)]),
                 (0, 'Nodes: 5', [(u'number_of_nodes', 5, None, None, None, None)]),
                 (0, u'Status: green', [])])],
          'shards': [(None,
                      {'active_shards_percent_as_number': (100.0, 50.0)},
                      [(0,
                        'Active primary: 4',
                        [(u'active_primary_shards', 4, None, None, None, None)]),
                       (0,
                        'Active: 8',
                        [(u'active_shards', 8, None, None, None, None)]),
                       (0,
                        'Active in percent: 100.00%',
                        [(u'active_shards_percent_as_number',
                          100.0,
                          None,
                          None,
                          None,
                          None)]),
                       (0,
                        'Delayed unassigned: 0',
                        [(u'delayed_unassigned_shards', 0, None, None, None, None)]),
                       (0,
                        'Initializing: 0',
                        [(u'initializing_shards', 0, None, None, None, None)]),
                       (0,
                        'Ongoing shard info requests: 0',
                        [(u'number_of_in_flight_fetch', 0, None, None, None, None)]),
                       (0,
                        'Relocating: 0',
                        [(u'relocating_shards', 0, None, None, None, None)]),
                       (0,
                        'Unassigned: 0',
                        [(u'unassigned_shards', 0, None, None, None, None)])])],
          'tasks': [(None,
                     {},
                     [(0,
                       'Pending tasks: 0.00',
                       [(u'number_of_pending_tasks', 0, None, None, None, None)]),
                      (0,
                       'Task max waiting: 0.00',
                       [(u'task_max_waiting_in_queue_millis',
                         0,
                         None,
                         None,
                         None,
                         None)]),
                      (0, u'Timed out: False', [])])]}
