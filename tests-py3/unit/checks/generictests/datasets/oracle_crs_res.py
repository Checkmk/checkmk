#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'oracle_crs_res'


info = [['oracle_host', 'NAME=ora.DG_CLUSTER.dg'],
        ['oracle_host', 'TYPE=ora.diskgroup.type'],
        ['oracle_host', 'STATE=ONLINE on oracle_host'],
        ['oracle_host', 'TARGET=ONLINE'],
]


discovery = {'': [('ora.DG_CLUSTER.dg', None)]}


checks = {'': [('ora.DG_CLUSTER.dg', {}, [(0, 'on oracle_host: online', [])])]}
