#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'mssql_blocked_sessions'


info = [['No blocking sessions']]


discovery = {'': [('', {})]}


checks = {'': [('', {'state': 2}, [(0, 'No blocking sessions', [])])]}
