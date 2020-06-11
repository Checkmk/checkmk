#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'mknotifyd'


info = [[u'[EX]'], [u'Binary file (standard input) matches']]


discovery = {'': [(u'EX', {})], 'connection': []}


checks = {'': [(u'EX',
                {},
                [(2,
                  'The state file seems to be empty or corrupted. It is very likely that the spooler is not working properly',
                  [])])]}
