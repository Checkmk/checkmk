#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'proxmox_version'

info = [
    [
        u'{"keyboard": "de", "release": "6.1", "repoid": "9bf06119", "version": "6.1-5"}'
    ]
]

discovery = {
    '': [
        (
            None, {
                u"discovered_release": u"6.1"
            }
        )
    ]
}

checks = {
    '': [(None, {
        u"discovered_release": u"6.1"
    }, [(0, "Version running: 6.1, Version during discovery: 6.1", [])])]
}
