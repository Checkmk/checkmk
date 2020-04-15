#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'kemp_loadmaster_services'


info = [['Foo', '1', '0'], ['Bar', '8', '0']]


discovery = {'': [('Bar', 'kemp_loadmaster_service_default_levels'),
                  ('Foo', 'kemp_loadmaster_service_default_levels')]}


checks = {'': [('Bar',
                (1500, 2000),
                [(3, 'Status: unknown[8]', []),
                 (0,
                  'Active connections: 0',
                  [('conns', 0, None, None, None, None)])]),
               ('Foo',
                (1500, 2000),
                [(0, 'Status: in service', []),
                 (0,
                  'Active connections: 0',
                 [('conns', 0, None, None, None, None)])])]}
