#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'cifsmounts'

info = [['/mnt/sias', 'ok', '2147723995', '313473446', '313473446', '2515456']]

discovery = {'': [('/mnt/sias', {})]}

checks = {'': [('/mnt/sias', {}, [(1, '85.4% used (4.10 of 4.80 PB)', [])])]}
