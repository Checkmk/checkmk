#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'kaspersky_av_kesl_updates'

info = [
    ["Name", "Kaspersky Endpoint Security 10 SP1 for Linux"],
    ["Version", "10.1.0.5960"],
    ["Key status", "Valid"],
    ["License expiration date", "2019-07-09"],
    ["Storage state", "No time limit for objects in Storage"],
    ["Storage space usage", "Storage size is unlimited"],
    ["Last run date of the Scan_My_Computer task", "Never run"],
    ["Last release date of databases", "2018-08-23 04:11:00"],
    ["Anti-virus databases loaded", "Yes"],
    ["Anti-virus database records", "11969941"],
    ["KSN state", "Off"],
    ["File monitoring", "Available and stopped"],
    ["Integrity monitoring", "Unavailable due to license limitation"],
    ["Firewall Management", "Available and stopped"],
    ["Anti-Cryptor", "Available and stopped"],
    ["Application update state", "No application updates available"],
]

discovery = {'': [(None, None)]}

checks = {
    '': [
        (
            None, {}, [
                (0, 'Databased loaded: True', []),
                (0, 'Database date: 2018-08-23 04:11:00', []),
                (0, 'Database record: 11969941', [])
            ]
        )
    ]
}
