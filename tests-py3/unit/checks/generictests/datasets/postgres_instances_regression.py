#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'postgres_instances'


info = [[u'[[[postgres]]]'],
        [u'30611',
         u'/usr/lib/postgresql/10/bin/postgres',
         u'-D',
         u'/var/lib/postgresql/10/main',
         u'-c',
         u'config_file=/etc/postgresql/10/main/postgresql.conf']]


discovery = {'': [(u'POSTGRES', {})]}


checks = {'': [(u'POSTGRES', {}, [(0, u'Status: running with PID 30611', [])])]}
