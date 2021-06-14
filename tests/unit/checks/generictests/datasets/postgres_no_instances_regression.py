#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'postgres_instances'

info = [
    [u'[[[postgres]]]'],
    [
        u'psql (PostgreSQL) 10.12 (Ubuntu 10.12-0ubuntu0.18.04.1)',
    ],
]

discovery = {'': [(u'POSTGRES', {})]}

checks = {'': [(u'POSTGRES', {}, [(2, u'Instance POSTGRES not running or postgres DATADIR name is not identical with instance name.', [])])]}
