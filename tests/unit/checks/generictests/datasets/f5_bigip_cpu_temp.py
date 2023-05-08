#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'f5_bigip_cpu_temp'

info = [['1', '40']]

discovery = {'': [('1', 'f5_bigip_cpu_temp_default_params')]}

checks = {
    '':
    [('1', (60, 80), [(0, '40 °C', [('temp', 40, 60.0, 80.0, None, None)])])]
}
