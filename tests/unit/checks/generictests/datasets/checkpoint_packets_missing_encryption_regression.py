#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'checkpoint_packets'

info = [[['1', '2', '3', '4']], []]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'accepted': (100000, 200000),
                'rejected': (100000, 200000),
                'dropped': (100000, 200000),
                'logged': (100000, 200000),
                'espencrypted': (100000, 200000),
                'espdecrypted': (100000, 200000)
            }, [
                (
                    0, 'Accepted: 0.0 pkts/s', [
                        ('accepted', 0.0, 100000, 200000, 0, None)
                    ]
                ),
                (
                    0, 'Rejected: 0.0 pkts/s', [
                        ('rejected', 0.0, 100000, 200000, 0, None)
                    ]
                ),
                (
                    0, 'Dropped: 0.0 pkts/s', [
                        ('dropped', 0.0, 100000, 200000, 0, None)
                    ]
                ),
                (
                    0, 'Logged: 0.0 pkts/s', [
                        ('logged', 0.0, 100000, 200000, 0, None)
                    ]
                )
            ]
        )
    ]
}
