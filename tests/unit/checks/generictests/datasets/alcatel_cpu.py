#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'alcatel_cpu'

info = [['17', 'doesnt matter', 'doesnt matter'], ['doesnt matter']]

discovery = {'': [(None, 'alcatel_cpu_default_levels')]}

checks = {'': [(None, (90.0, 95.0), [(0, 'total: 17.0%', [('util', 17, 90.0, 95.0, 0, 100)])])]}
