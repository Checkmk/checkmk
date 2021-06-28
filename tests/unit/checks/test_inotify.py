#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

import pytest  # type: ignore[import]

from testlib import Check  # type: ignore[import]

pytestmark = pytest.mark.checks

INFO = [
    ["warning:", "I assume a warning looks like this!"],
    ["configured", "folder", "/tmp/noti"],
    ["configured", "file", "/tmp/noti/test"],
    ["configured", "file", "/tmp/noti/nodata"],
    ["1465470055", "modify", "/tmp/noti/test", "5", "1465470055"],
    ["1465470055", "open", "/tmp/noti/test", "5", "1465470055"],
    ["1465470055", "modify", "/tmp/noti/test", "5", "1465470055"],
    ["1465470056", "modify", "/tmp/noti/test", "5", "1465470056"],
    ["1465470056", "open", "/tmp/noti/test", "5", "1465470056"],
    ["1465470058", "delete", "/tmp/noti/test"],
]

PARSED = {
    'configured': {
        'file': {'/tmp/noti/nodata', '/tmp/noti/test'},
        'folder': {'/tmp/noti'}
    },
    'meta': {
        'warnings': {
            'I assume a warning looks like this!': 1
        }
    },
    'stats': {
        '/tmp/noti': [{
            'mode': 'modify',
            'mtime': '1465470055',
            'size': '5',
            'timestamp': 1465470055
        }, {
            'mode': 'open',
            'mtime': '1465470055',
            'size': '5',
            'timestamp': 1465470055
        }, {
            'mode': 'modify',
            'mtime': '1465470055',
            'size': '5',
            'timestamp': 1465470055
        }, {
            'mode': 'modify',
            'mtime': '1465470056',
            'size': '5',
            'timestamp': 1465470056
        }, {
            'mode': 'open',
            'mtime': '1465470056',
            'size': '5',
            'timestamp': 1465470056
        }, {
            'mode': 'delete',
            'timestamp': 1465470058
        }],
        '/tmp/noti/test': [{
            'mode': 'modify',
            'mtime': '1465470055',
            'size': '5',
            'timestamp': 1465470055
        }, {
            'mode': 'open',
            'mtime': '1465470055',
            'size': '5',
            'timestamp': 1465470055
        }, {
            'mode': 'modify',
            'mtime': '1465470055',
            'size': '5',
            'timestamp': 1465470055
        }, {
            'mode': 'modify',
            'mtime': '1465470056',
            'size': '5',
            'timestamp': 1465470056
        }, {
            'mode': 'open',
            'mtime': '1465470056',
            'size': '5',
            'timestamp': 1465470056
        }, {
            'mode': 'delete',
            'timestamp': 1465470058
        }]
    },
}


def test_inotify_parse():
    parse_inotify = Check("inotify").context["parse_inotify"]
    assert PARSED == parse_inotify(INFO)


def test_discovery():
    discover_inotify = Check("inotify").context["inventory_inotify"]
    assert sorted(discover_inotify(PARSED)) == [
        ('File /tmp/noti/nodata', {}),
        ('File /tmp/noti/test', {}),
        ('Folder /tmp/noti', {}),
    ]


def test_updated_data():
    check_inotify = Check("inotify").context["_check_inotify"]
    item = "Folder /tmp/noti"
    params = {
        'age_last_operation': [
            ('modify', 90, 110),
            ('open', 80, 90),
            ('just_for_test_coverage', 1, 2),
        ]
    }
    last_status: Dict = {}
    now = 1465470156

    assert list(check_inotify(item, params, PARSED, last_status, now)) == [
        (0, 'Last Delete: 98 s ago'),
        (1, 'Last Modify: 100 s ago (> 90 s)'),
        (2, 'Last Open: 100 s ago (> 90 s)'),
        (3, 'Last Just_For_Test_Coverage unknown'),
        (1, 'Incomplete data!'),
        (1, '1 Warnings: I assume a warning looks like this!'),
    ]
    assert last_status == {
        'delete': {
            'mode': 'delete',
            'timestamp': 1465470058
        },
        'modify': {
            'mode': 'modify',
            'mtime': '1465470056',
            'size': '5',
            'timestamp': 1465470056
        },
        'open': {
            'mode': 'open',
            'mtime': '1465470056',
            'size': '5',
            'timestamp': 1465470056
        },
    }


def test_nodata():
    check_inotify = Check("inotify").context["_check_inotify"]
    item = "File /tmp/noti/nodata"
    params = {'age_last_operation': [('modify', 90, 110)]}
    last_status: Dict = {}
    now = 1465470156

    assert list(check_inotify(item, params, PARSED, last_status, now)) == [
        (3, 'Last Modify unknown'),
        (1, 'Incomplete data!'),
        (1, '1 Warnings: I assume a warning looks like this!'),
        (0, 'No data available yet'),
    ]
    assert not last_status


def test_old_status():
    check_inotify = Check("inotify").context["_check_inotify"]
    item = "File /tmp/noti/nodata"
    params = {'age_last_operation': [('modify', 90, 110)]}
    last_status = {'modify': {"timestamp": 1465470000}}
    now = 1465470156

    assert list(check_inotify(item, params, PARSED, last_status, now)) == [
        (2, 'Last Modify: 156 s ago (> 110 s)'),
        (1, 'Incomplete data!'),
        (1, '1 Warnings: I assume a warning looks like this!'),
    ]
    assert last_status == {'modify': {"timestamp": 1465470000}}
