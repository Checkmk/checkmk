#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import Check


def test_parse_simple():
    check = Check("arista_bgp")
    data = [
        [
            [192, 168, 1, 1],
            [10, 10, 10, 10],
            "65000",
            [192, 168, 2, 0],
            "2",
            "6",
            "Cease/other configuration change",
            "1.1.4.192.168.1.2",
        ]
    ]
    assert check.run_parse([data]) == {
        "192.168.1.2": {
            "Admin state": "running",
            "BGP version": 4,
            "Last received error": "Cease/other configuration change",
            "Local address": "192.168.1.1",
            "Local identifier": "10.10.10.10",
            "Peer state": "established",
            "Remote AS number": 65000,
            "Remote identifier": "192.168.2.0",
        }
    }


def test_parse_empty_address():
    check = Check("arista_bgp")
    data = [
        [
            [],
            [0, 0, 0, 0],
            "65007",
            [0, 0, 0, 0],
            "2",
            "1",
            "",
            "1.1.4.192.168.1.2",
        ]
    ]
    assert check.run_parse([data]) == {
        "192.168.1.2": {
            "Admin state": "running",
            "BGP version": 4,
            "Last received error": "",
            "Local address": "empty()",
            "Local identifier": "0.0.0.0",
            "Peer state": "idle",
            "Remote AS number": 65007,
            "Remote identifier": "0.0.0.0",
        },
    }
