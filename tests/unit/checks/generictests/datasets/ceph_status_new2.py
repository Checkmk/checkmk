#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'ceph_status'


info = [['{'],
        ['"fsid":', '"123-abc-456",'],
        ['"health":', '{'],
        ['"checks":', '{'],
        ['"err_0":', '{'],
        ['"summary":', '{'],
        ['"message":', '"any', 'error', '1"'],
        ['}'],
        ['},'],
        ['"err_1":', '{'],
        ['"summary":', '{'],
        ['"message":', '"any', 'error', '2"'],
        ['}'],
        ['},'],
        ['"err_2":', '{'],
        ['"summary":', '{}'],
        ['},'],
        ['"err_3":', '{}'],
        ['},'],
        ['"status":', '"HEALTH_WARN",'],
        ['"summary":', '['],
        ['{'],
        ['"severity":', '"HEALTH_WARN",'],
        ['"summary":',
         '"\'ceph',
         "health'",
         'JSON',
         'format',
         'has',
         'changed',
         'in',
         'luminous.',
         'If',
         'you',
         'see',
         'this',
         'your',
         'monitoring',
         'system',
         'is',
         'scraping',
         'the',
         'wrong',
         'fields.',
         'Disable',
         'this',
         'with',
         "'mon",
         'health',
         'preluminous',
         'compat',
         'warning',
         '=',
         'false\'"'],
        ['}'],
        ['],'],
        ['"overall_status":', '"HEALTH_WARN"'],
        ['},'],
        ['"election_epoch":', '2020'],
        ['}']]


discovery = {'': [(None, {})], 'mgrs': [], 'osds': [], 'pgs': []}


checks = {'': [(None,
                {'epoch': (1, 3, 30)},
                [(1, 'Health: warning (any error 1, any error 2)', []), (0, 'Epoch rate (30 minutes 0 seconds average): 0.00', [])])]}
