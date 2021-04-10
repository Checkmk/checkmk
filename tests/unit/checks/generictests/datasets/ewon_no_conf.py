#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'ewon'

info = []


discovery = {
    '': [
        ('eWON Status', {'device': None}),
    ],
}


checks = {
    '': [
        ('eWON Status', {'device': None}, [
            (1, 'This device requires configuration. Please pick the device type.', []),
        ]),
    ],
}
