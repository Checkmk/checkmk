#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'dell_compellent_disks'

info = [[
    [u'1', u'1', u'1', u'', u'1'],
    [u'2', u'999', u'1', u'', u'1'],
    [u'3', u'1', u'999', u'', u'1'],
    [u'4', u'1', u'0', u'ATTENTION', u'1'],
    [u'5', u'1', u'999', u'ATTENTION', u'1'],
    [u'10', u'2', u'0', u'KAPUTT', u'1'],
], [
    [u'serial1'], [u'serial2'], [u'serial3'], [u'serial4'], [u'serial5'], [u'serial10']
]]

discovery = {
    '': [(u'1', {}), (u'2', {}), (u'3', {}), (u'4', {}), (u'5', {}), (u'10', {})]
}

checks = {
    '': [
        (u'1', {}, [
            (0, 'Status: UP', []),
            (0, u'Location: Enclosure 1', []),
            (0, "Serial number: serial1", []),
        ]),
        (u'2', {}, [
            (3, u'Status: unknown[999]', []),
            (0, u'Location: Enclosure 1', []),
            (0, "Serial number: serial2", []),
        ]),
        (u'3', {}, [
            (0, 'Status: UP', []),
            (0, u'Location: Enclosure 1', []),
            (0, "Serial number: serial3", []),
        ]),
        (u'4', {}, [
            (0, 'Status: UP', []),
            (0, u'Location: Enclosure 1', []),
            (0, "Serial number: serial4", []),
            (2, u'Health: not healthy, Reason: ATTENTION', []),
        ]),
        (u'5', {}, [
            (0, 'Status: UP', []),
            (0, u'Location: Enclosure 1', []),
            (0, "Serial number: serial5", []),
            (3, u'Health: unknown[999], Reason: ATTENTION', []),
        ]),
        (u'10', {}, [
            (2, 'Status: DOWN', []),
            (0, u'Location: Enclosure 1', []),
            (0, "Serial number: serial10", []),
            (2, u'Health: not healthy, Reason: KAPUTT', []),
        ]),
    ]
}
