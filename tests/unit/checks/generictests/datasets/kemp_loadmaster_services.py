#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'kemp_loadmaster_services'


info = [['vs adaptive method type', '1', '100'],
        ['another vs adaptive method type', '1', '200'],
        ['yet another vs adaptive method type', '4', '100']]


discovery = {'': [('another vs adaptive method type',
                   'kemp_loadmaster_service_default_levels'),
                  ('vs adaptive method type', 'kemp_loadmaster_service_default_levels')]}


checks = {'': [('another vs adaptive method type',
                (1500, 2000),
                [(0, 'Status: in service', []),
                 (0,
                  'Active connections: 200',
                  [('conns', 200, None, None, None, None)])]),
               ('vs adaptive method type',
                (1500, 2000),
                [(0, 'Status: in service', []),
                 (0,
                  'Active connections: 100',
                  [('conns', 100, None, None, None, None)])])]}
