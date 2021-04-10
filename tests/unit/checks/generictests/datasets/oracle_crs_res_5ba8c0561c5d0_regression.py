#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'oracle_crs_res'


info = [[u'NAME=ora.ARCH.dg'],
        [u'TYPE=ora.diskgroup.type'],
        [u'STATE=ONLINE'],
        [u'TARGET=ONLINE'],
        [u'ENABLED=1'],
        [u'NAME=ora.DATA.dg'],
        [u'TYPE=ora.diskgroup.type'],
        [u'STATE=ONLINE'],
        [u'TARGET=ONLINE'],
        [u'ENABLED=1']]


discovery = {'': [(u'ora.ARCH.dg', None), (u'ora.DATA.dg', None)]}


checks = {'': [(u'ora.ARCH.dg', {}, [(0, u'online', [])]),
               (u'ora.DATA.dg', {}, [(0, u'online', [])])]}
