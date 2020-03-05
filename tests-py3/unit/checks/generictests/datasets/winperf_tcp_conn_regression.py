#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'winperf_tcp_conn'


info = [['1557816444.39', '638', '2156250'],
        ['2', '53267', 'counter'],
        ['4', '3', 'rawcount'],
        ['6', '23', 'rawcount'],
        ['8', '1', 'rawcount'],
        ['10', '1', 'rawcount'],
        ['12', '12', 'rawcount'],
        ['14', '34830', 'counter'],
        ['16', '18437', 'counter']]


discovery = {'': [(None, 'tcp_conn_stats_default_levels')]}


checks = {'': [(None,
                {},
                [(0, 'ESTABLISHED: 3', []),
                 (0, '', [('ESTABLISHED', 3, None, None, None, None)])])]}
