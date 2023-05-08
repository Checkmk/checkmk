#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'cmctc_state'


info = [[u'4', u'1']]


discovery = {'': [(None, {})]}


checks = {'': [(None, {}, [(2, u'Status: unknown[4], Units connected: 1', [])])]}
