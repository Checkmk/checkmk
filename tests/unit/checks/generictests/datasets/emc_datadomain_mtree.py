#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'emc_datadomain_mtree'


info = [['/data/col1/boost_vmware', '3943.3', '3'],
        ['/data/col1/repl_cms_dc1', '33.3', '2'],
        ['/data/col1/nfs_cms_dc1', '0.0', '1'],
        ['something', '0.0', '-1']]


discovery = {'': [('/data/col1/boost_vmware', {}),
                  ('/data/col1/repl_cms_dc1', {}),
                  ('/data/col1/nfs_cms_dc1', {}),
                  ('something', {})]}


_factory_settings = {"deleted": 2,
                     "read-only": 1,
                     "read-write": 0,
                     "replication destination": 0,
                     "retention lock disabled": 0,
                     "retention lock enabled": 0,
                     "unknown": 3}

checks = {'': [('/data/col1/boost_vmware',
                _factory_settings,
                [(0, 'Status: read-write, Precompiled: 3.85 TiB',
                  [('precompiled', 4234086134579)])]),
               ('/data/col1/repl_cms_dc1',
                _factory_settings,
                [(1, 'Status: read-only, Precompiled: 33.3 GiB', [('precompiled', 35755602739)])]),
               ('/data/col1/nfs_cms_dc1',
                _factory_settings,
                [(2, 'Status: deleted, Precompiled: 0 B', [('precompiled', 0)])]),
               ('something',
                _factory_settings,
                [(3, 'Status: invalid code -1, Precompiled: 0 B', [('precompiled', 0)])])]}
