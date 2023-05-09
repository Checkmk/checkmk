#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'f5_bigip_apm'

info = [['0']]

discovery = {'': [(None, None)]}

checks = {
    '': [
        (
            None, {}, [
                (
                    0, 'Connections: 0', [
                        ('connections_ssl_vpn', 0, None, None, 0, None)
                    ]
                )
            ]
        )
    ]
}
