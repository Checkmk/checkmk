#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]
from checktestlib import DiscoveryResult, assertDiscoveryResultsEqual, assertEqual

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info, expected_parse_result",
    [
        (
            [
                ['[SNIP]'],
                ['dataset13', 'name', 'dataset13', '-'],
                ['dataset13', 'quota', '0', 'local'],
                ['dataset13', 'used', '33419296463072', '-'],
                ['dataset13', 'available', '11861098415520', '-'],
                ['dataset13', 'mountpoint', '/mnt/dataset13', 'default'],
                ['dataset13', 'type', 'filesystem', '-'],
                ['[SNIP]'],
                ['dataset13/MyFolder', 'name', 'dataset13/MyFolder', '-'],
                ['dataset13/MyFolder', 'quota', '5497558138880', 'local'],
                ['dataset13/MyFolder', 'used', '5497558146368', '-'],
                ['dataset13/MyFolder', 'available', '0', '-'],
                ['dataset13/MyFolder', 'mountpoint', '/mnt/dataset13/MyFolder', 'default'],
                ['dataset13/MyFolder', 'type', 'filesystem', '-'],
                ['[SNIP]'],
                ['[df]'],
                ['[SNIP]'],
                ['dataset13', '11583104083', '162', '11583103921', '0%', '/mnt/dataset13'],
                ['[SNIP]'],
                [
                    'dataset13/MyFolder', '5368709127', '5368709127', '0', '100%',
                    '/mnt/dataset13/MyFolder'
                ],
                ['[SNIP]'],
            ],
            {
                '/mnt/dataset13': {
                    'name': 'dataset13',
                    'used': 31871124.709197998,
                    'available': 11311624.923248291,
                    'mountpoint': '/mnt/dataset13',
                    'type': 'filesystem',
                    'is_pool': True
                },
                '/mnt/dataset13/MyFolder': {
                    'name': 'dataset13/MyFolder',
                    'quota': 5242880.0,
                    'used': 5242880.007141113,
                    'available': 0.0,
                    'mountpoint': '/mnt/dataset13/MyFolder',
                    'type': 'filesystem',
                    'is_pool': False
                },
            },
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_zfsget_parse(info, expected_parse_result):
    assertEqual(Check("zfsget").run_parse(info), expected_parse_result)


@pytest.mark.parametrize(
    "info,expected_discovery_result",
    [
        ([], []),
        # no zfsget items and no df item
        (
            [
                [u'[zfs]'],
                [u'[df]'],
            ],
            [],
        ),
        # separator df: whitespace
        # no zfsget items and pass-through filesystem
        (
            [
                [u'[zfs]'],
                [u'[df]'],
                [u'/', u'10255636', u'1836517', u'8419119', u'18%', u'/'],
                [u'/dev', u'10255636', u'1836517', u'8419119', u'18%', u'/dev'],
                [u'foo', u'zfs', u'457758604', u'88', u'457758516', u'0%', u'/mnt/foo'],
                [u'foo/bar', u'zfs', u'45977', u'2012596', u'457758516', u'0%', u'/mnt/foo/bar'],
            ],
            [("/mnt/foo", {}), ("/mnt/foo/bar", {}), ("/", {})],
        ),
        # separator df: whitespace
        # no zfsget items and pass-through filesystem
        (
            [
                [u'[zfs]'],
                [u'[df]'],
                [u'/', u'10255636', u'1836517', u'8419119', u'18%', u'/'],
                [u'/dev', u'10255636', u'1836517', u'8419119', u'18%', u'/dev'],
            ],
            [("/", {})],
        ),
        # separator zfs: tab
        # separator df: whitespace
        # no whitespace in device-names/mountpoints
        (
            [
                [u'[zfs]'],
                [u'foo', u'name', u'foo', u'-'],
                [u'foo', u'quota', u'0', u'default'],
                [u'foo', u'used', u'9741332480', u'-'],
                [u'foo', u'available', u'468744720384', u'-'],
                [u'foo', u'mountpoint', u'/mnt/foo', u'default'],
                [u'foo', u'type', u'filesystem', u'-'],
                [u'foo/bar-baz', u'name', u'foo/bar-baz', u'-'],
                [u'foo/bar-baz', u'quota', u'0', u'default'],
                [u'foo/bar-baz', u'used', u'2060898304', u'-'],
                [u'foo/bar-baz', u'available', u'468744720384', u'-'],
                [u'foo/bar-baz', u'mountpoint', u'/mnt/foo/bar-baz', u'default'],
                [u'foo/bar-baz', u'type', u'filesystem', u'-'],
                [u'[df]'],
                [u'/', u'10255636', u'1836517', u'8419119', u'18%', u'/'],
                [u'/dev', u'10255636', u'1836517', u'8419119', u'18%', u'/dev'],
                [u'foo', u'457758604', u'88', u'457758516', u'0%', u'/mnt/foo'],
                [u'foo/bar-baz', u'45977', u'2012596', u'457758516', u'0%', u'/mnt/foo/bar-baz'],
            ],
            [("/mnt/foo/bar-baz", {}), ("/mnt/foo", {}), ("/", {})],
        ),
        # separator zfs: tab
        # separator df: whitespace
        # no whitespace in device-names/mountpoints + FS_TYPE
        (
            [
                [u'[zfs]'],
                [u'foo', u'name', u'foo', u'-'],
                [u'foo', u'quota', u'0', u'default'],
                [u'foo', u'used', u'9741332480', u'-'],
                [u'foo', u'available', u'468744720384', u'-'],
                [u'foo', u'mountpoint', u'/mnt/foo', u'default'],
                [u'foo', u'type', u'filesystem', u'-'],
                [u'foo/bar', u'baz', u'name', u'foo/bar', u'-'],
                [u'foo/bar', u'baz', u'quota', u'0', u'default'],
                [u'foo/bar', u'baz', u'used', u'2060898304', u'-'],
                [u'foo/bar', u'baz', u'available', u'468744720384', u'-'],
                [u'foo/bar', u'baz', u'mountpoint', u'/mnt/foo/bar', u'default'],
                [u'foo/bar', u'baz', u'type', u'filesystem', u'-'],
                [u'[df]'],
                [u'/', u'10255636', u'1836517', u'8419119', u'18%', u'/'],
                [u'/dev', u'10255636', u'1836517', u'8419119', u'18%', u'/dev'],
                [u'foo', u'zfs', u'457758604', u'88', u'457758516', u'0%', u'/mnt/foo'],
                [u'foo/bar', u'zfs', u'45977', u'2012596', u'457758516', u'0%', u'/mnt/foo/bar'],
            ],
            [("/mnt/foo", {}), ("/mnt/foo/bar", {}), ("/", {})],
        ),
        # separator: tab
        # no whitespace in device-names/mountpoints
        (
            [
                [u'foo', u'name', u'foo', u'-'],
                [u'foo', u'quota', u'0', u'default'],
                [u'foo', u'used', u'9741332480', u'-'],
                [u'foo', u'available', u'468744720384', u'-'],
                [u'foo', u'mountpoint', u'/mnt/foo', u'default'],
                [u'foo', u'type', u'filesystem', u'-'],
                [u'foo/bar-baz', u'name', u'foo/bar-baz', u'-'],
                [u'foo/bar-baz', u'quota', u'0', u'default'],
                [u'foo/bar-baz', u'used', u'2060898304', u'-'],
                [u'foo/bar-baz', u'available', u'468744720384', u'-'],
                [u'foo/bar-baz', u'mountpoint', u'/mnt/foo/bar-baz', u'default'],
                [u'foo/bar-baz', u'type', u'filesystem', u'-'],
                [u'[df]'],
                [u'/                    10255636 1836517 8419119    18%    /'],
                [u'/dev                 10255636 1836517 8419119    18%    /dev'],
                [u'foo                       457758604      88  457758516     0%    /mnt/foo'],
                [u'foo/bar-baz              45977 2012596  457758516     0%    /mnt/foo/bar-baz'],
            ],
            [("/mnt/foo/bar-baz", {}), ("/mnt/foo", {}), ("/", {})],
        ),
        # separator: tab
        # no whitespace in device-names/mountpoints + FS_TYPE
        (
            [
                [u'[zfs]'],
                [u'foo', u'name', u'foo', u'-'],
                [u'foo', u'quota', u'0', u'default'],
                [u'foo', u'used', u'9741332480', u'-'],
                [u'foo', u'available', u'468744720384', u'-'],
                [u'foo', u'mountpoint', u'/mnt/foo', u'default'],
                [u'foo', u'type', u'filesystem', u'-'],
                [u'foo/bar-baz', u'name', u'foo/bar-baz', u'-'],
                [u'foo/bar-baz', u'quota', u'0', u'default'],
                [u'foo/bar-baz', u'used', u'2060898304', u'-'],
                [u'foo/bar-baz', u'available', u'468744720384', u'-'],
                [u'foo/bar-baz', u'mountpoint', u'/mnt/foo/bar-baz', u'default'],
                [u'foo/bar-baz', u'type', u'filesystem', u'-'],
                [u'[df]'],
                [u'/                    10255636 1836517 8419119    18%    /'],
                [u'/dev                 10255636 1836517 8419119    18%    /dev'],
                [u'foo           zfs         457758604      88  457758516     0%    /mnt/foo'],
                [u'foo/bar-baz   zfs        45977 2012596  457758516     0%    /mnt/foo/bar-baz'],
            ],
            [("/mnt/foo/bar-baz", {}), ("/mnt/foo", {}), ("/", {})],
        ),
        # separator: tab
        # with whitespace in device-names/mountpoints
        (
            [
                [u'[zfs]'],
                [u'f oo', u'name', u'f oo', u'-'],
                [u'f oo', u'quota', u'0', u'default'],
                [u'f oo', u'used', u'9741332480', u'-'],
                [u'f oo', u'available', u'468744720384', u'-'],
                [u'f oo', u'mountpoint', u'/mnt/f oo', u'default'],
                [u'f oo', u'type', u'filesystem', u'-'],
                [u'f oo/bar baz', u'name', u'f oo/bar baz', u'-'],
                [u'f oo/bar baz', u'quota', u'0', u'default'],
                [u'f oo/bar baz', u'used', u'2060898304', u'-'],
                [u'f oo/bar baz', u'available', u'468744720384', u'-'],
                [u'f oo/bar baz', u'mountpoint', u'/mnt/f oo/bar baz', u'default'],
                [u'f oo/bar baz', u'type', u'filesystem', u'-'],
                [u'[df]'],
                [u'/                    10255636 1836517 8419119    18%    /'],
                [u'/dev                 10255636 1836517 8419119    18%    /dev'],
                [u'f oo                       457758604      88  457758516     0%    /mnt/f oo'],
                [u'f oo/bar baz              45977 2012596  457758516     0%    /mnt/f oo/bar baz'],
            ],
            [("/mnt/f oo/bar baz", {}), ("/mnt/f oo", {}), ("/", {})],
        ),
        # separator zfs: tab
        # separator df: whitespace
        # with whitespace in device-names/mountpoints
        (
            [
                [u'[zfs]'],
                [u'f', u'oo', u'name', u'f', u'oo', u'-'],
                [u'f', u'oo', u'quota', u'0', u'default'],
                [u'f', u'oo', u'used', u'9741332480', u'-'],
                [u'f', u'oo', u'available', u'468744720384', u'-'],
                [u'f', u'oo', u'mountpoint', u'/mnt/f', u'oo', u'default'],
                [u'f', u'oo', u'type', u'filesystem', u'-'],
                [u'f', u'oo/bar', u'baz', u'name', u'f', u'oo/bar', u'baz', u'-'],
                [u'f', u'oo/bar', u'baz', u'quota', u'0', u'default'],
                [u'f', u'oo/bar', u'baz', u'used', u'2060898304', u'-'],
                [u'f', u'oo/bar', u'baz', u'available', u'468744720384', u'-'],
                [u'f', u'oo/bar', u'baz', u'mountpoint', u'/mnt/f', u'oo/bar', u'baz', u'default'],
                [u'f', u'oo/bar', u'baz', u'type', u'filesystem', u'-'],
                [u'[df]'],
                [u'/', u'10255636', u'1836517', u'8419119', u'18%', u'/'],
                [u'/dev', u'10255636', u'1836517', u'8419119', u'18%', u'/dev'],
                [u'f', u'oo', u'457758604', u'88', u'457758516', u'0%', u'/mnt/f', u'oo'],
                [
                    u'f', u'oo/bar', u'baz', u'45977', u'2012596', u'457758516', u'0%', u'/mnt/f',
                    u'oo/bar', u'baz'
                ],
            ],
            [("/mnt/f oo/bar baz", {}), ("/mnt/f oo", {}), ("/", {})],
        ),
        # separator zfs: tab
        # separator df: whitespace
        # with whitespace in device-names/mountpoints + FS_TYPE
        (
            [
                [u'[zfs]'],
                [u'f', u'oo', u'name', u'f', u'oo', u'-'],
                [u'f', u'oo', u'quota', u'0', u'default'],
                [u'f', u'oo', u'used', u'9741332480', u'-'],
                [u'f', u'oo', u'available', u'468744720384', u'-'],
                [u'f', u'oo', u'mountpoint', u'/mnt/f', u'oo', u'default'],
                [u'f', u'oo', u'type', u'filesystem', u'-'],
                [u'f', u'oo/bar', u'baz', u'name', u'f', u'oo/bar', u'baz', u'-'],
                [u'f', u'oo/bar', u'baz', u'quota', u'0', u'default'],
                [u'f', u'oo/bar', u'baz', u'used', u'2060898304', u'-'],
                [u'f', u'oo/bar', u'baz', u'available', u'468744720384', u'-'],
                [u'f', u'oo/bar', u'baz', u'mountpoint', u'/mnt/f', u'oo/bar', u'baz', u'default'],
                [u'f', u'oo/bar', u'baz', u'type', u'filesystem', u'-'],
                [u'[df]'],
                [u'/', u'10255636', u'1836517', u'8419119', u'18%', u'/'],
                [u'/dev', u'10255636', u'1836517', u'8419119', u'18%', u'/dev'],
                [u'f', u'oo', u'zfs', u'457758604', u'88', u'457758516', u'0%', u'/mnt/f', u'oo'],
                [
                    u'f', u'oo/bar', u'baz', u'zfs', u'45977', u'2012596', u'457758516', u'0%',
                    u'/mnt/f', u'oo/bar', u'baz'
                ],
            ],
            [("/mnt/f oo/bar baz", {}), ("/mnt/f oo", {}), ("/", {})],
        ),
    ])
@pytest.mark.usefixtures("config_load_all_checks")
def test_zfsget_discovery(info, expected_discovery_result):
    check_zfsget = Check("zfsget")
    discovery_result = DiscoveryResult(check_zfsget.run_discovery(check_zfsget.run_parse(info)))
    assertDiscoveryResultsEqual("zfsget", discovery_result,
                                DiscoveryResult(expected_discovery_result))
