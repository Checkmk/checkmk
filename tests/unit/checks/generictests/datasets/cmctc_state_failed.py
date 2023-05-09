#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'cmctc_state'


info = [['1', '3']]


discovery = {'': [(None, {})]}


checks = {'': [(None, {}, [(2, 'Status: failed, Units connected: 3', [])])]}
