#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'hyperv_vmstatus'


info = [
    ["Integration_Services", "Protocol_Mismatch"],
    ["Replica_Health", "None"],
]


discovery = {'': [(None, {})]}


checks = {
    '': [
        (None, {}, [
            (0, 'Integration Service State: Protocol_Mismatch', []),
        ]),
    ],
}
