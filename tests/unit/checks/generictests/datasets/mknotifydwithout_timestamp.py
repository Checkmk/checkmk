#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'mknotifyd'


freeze_time = '2019-05-22T14:00:00'


info = [['[heute]'],
        ['Version: 2015.09.18'],
        ['Updated: 1443780550 (2015-10-02 12:09:10)'],
        ['Started: 1443774555 (2015-10-02 10:29:15, 5994 sec ago)'],
        ['Configuration: 1443774555 (2015-10-02 10:29:15, 5994 sec ago)'],
        ['Listening FD: None'],
        ['Spool: New'],
        ['Count: 0'],
        ['Oldest: 1443774555 (2015-10-02 10:29:15, 5994 sec ago)'],
        ['Youngest:'],
        ['Spool: Deferred'],
        ['Count: 0'],
        ['Oldest: 1443774555 (2015-10-02 10:29:15, 5994 sec ago)'],
        ['Youngest:'],
        ['Spool: Corrupted'],
        ['Count: 4'],
        ['Oldest: 1443774555 (2015-10-02 10:29:15, 5994 sec ago)'],
        ['Youngest: 1443780550 (2015-10-02 12:09:10)']]


discovery = {'': [('heute', {})], 'connection': []}


checks = {'': [('heute',
                {},
                [(0, 'Version: 2015.09.18', []),
                 (2,
                  'Status last updated 3 years 233 days ago, spooler seems crashed or busy',
                  [('last_updated', 114753050.0, None, None, None, None),
                   ('new_files', 0, None, None, None, None)]),
                 (1,
                  '4 corrupted files: youngest 3 years 233 days ago',
                  [('corrupted_files', 4, None, None, None, None)])])]}
