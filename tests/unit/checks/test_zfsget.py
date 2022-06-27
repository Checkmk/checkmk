#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from .checktestlib import assertDiscoveryResultsEqual, assertEqual, DiscoveryResult

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info, expected_parse_result",
    [
        (
            [
                ["[SNIP]"],
                ["dataset13", "name", "dataset13", "-"],
                ["dataset13", "quota", "0", "local"],
                ["dataset13", "used", "33419296463072", "-"],
                ["dataset13", "available", "11861098415520", "-"],
                ["dataset13", "mountpoint", "/mnt/dataset13", "default"],
                ["dataset13", "type", "filesystem", "-"],
                ["[SNIP]"],
                ["dataset13/MyFolder", "name", "dataset13/MyFolder", "-"],
                ["dataset13/MyFolder", "quota", "5497558138880", "local"],
                ["dataset13/MyFolder", "used", "5497558146368", "-"],
                ["dataset13/MyFolder", "available", "0", "-"],
                ["dataset13/MyFolder", "mountpoint", "/mnt/dataset13/MyFolder", "default"],
                ["dataset13/MyFolder", "type", "filesystem", "-"],
                ["[SNIP]"],
                ["[df]"],
                ["[SNIP]"],
                ["dataset13", "11583104083", "162", "11583103921", "0%", "/mnt/dataset13"],
                ["[SNIP]"],
                [
                    "dataset13/MyFolder",
                    "5368709127",
                    "5368709127",
                    "0",
                    "100%",
                    "/mnt/dataset13/MyFolder",
                ],
                ["[SNIP]"],
            ],
            {
                "/mnt/dataset13": {
                    "name": "dataset13",
                    "used": 31871124.709197998,
                    "available": 11311624.923248291,
                    "mountpoint": "/mnt/dataset13",
                    "type": "filesystem",
                    "is_pool": True,
                },
                "/mnt/dataset13/MyFolder": {
                    "name": "dataset13/MyFolder",
                    "quota": 5242880.0,
                    "used": 5242880.007141113,
                    "available": 0.0,
                    "mountpoint": "/mnt/dataset13/MyFolder",
                    "type": "filesystem",
                    "is_pool": False,
                },
            },
        ),
    ],
)
def test_zfsget_parse(info, expected_parse_result) -> None:
    assertEqual(Check("zfsget").run_parse(info), expected_parse_result)


@pytest.mark.parametrize(
    "info,expected_discovery_result",
    [
        ([], []),
        # no zfsget items and no df item
        (
            [
                ["[zfs]"],
                ["[df]"],
            ],
            [],
        ),
        # separator df: whitespace
        # no zfsget items and pass-through filesystem
        (
            [
                ["[zfs]"],
                ["[df]"],
                ["/", "10255636", "1836517", "8419119", "18%", "/"],
                ["/dev", "10255636", "1836517", "8419119", "18%", "/dev"],
                ["foo", "zfs", "457758604", "88", "457758516", "0%", "/mnt/foo"],
                ["foo/bar", "zfs", "45977", "2012596", "457758516", "0%", "/mnt/foo/bar"],
            ],
            [("/mnt/foo", {}), ("/mnt/foo/bar", {}), ("/", {})],
        ),
        # separator df: whitespace
        # no zfsget items and pass-through filesystem
        (
            [
                ["[zfs]"],
                ["[df]"],
                ["/", "10255636", "1836517", "8419119", "18%", "/"],
                ["/dev", "10255636", "1836517", "8419119", "18%", "/dev"],
            ],
            [("/", {})],
        ),
        # separator zfs: tab
        # separator df: whitespace
        # no whitespace in device-names/mountpoints
        (
            [
                ["[zfs]"],
                ["foo", "name", "foo", "-"],
                ["foo", "quota", "0", "default"],
                ["foo", "used", "9741332480", "-"],
                ["foo", "available", "468744720384", "-"],
                ["foo", "mountpoint", "/mnt/foo", "default"],
                ["foo", "type", "filesystem", "-"],
                ["foo/bar-baz", "name", "foo/bar-baz", "-"],
                ["foo/bar-baz", "quota", "0", "default"],
                ["foo/bar-baz", "used", "2060898304", "-"],
                ["foo/bar-baz", "available", "468744720384", "-"],
                ["foo/bar-baz", "mountpoint", "/mnt/foo/bar-baz", "default"],
                ["foo/bar-baz", "type", "filesystem", "-"],
                ["[df]"],
                ["/", "10255636", "1836517", "8419119", "18%", "/"],
                ["/dev", "10255636", "1836517", "8419119", "18%", "/dev"],
                ["foo", "457758604", "88", "457758516", "0%", "/mnt/foo"],
                ["foo/bar-baz", "45977", "2012596", "457758516", "0%", "/mnt/foo/bar-baz"],
            ],
            [("/mnt/foo/bar-baz", {}), ("/mnt/foo", {}), ("/", {})],
        ),
        # separator zfs: tab
        # separator df: whitespace
        # no whitespace in device-names/mountpoints + FS_TYPE
        (
            [
                ["[zfs]"],
                ["foo", "name", "foo", "-"],
                ["foo", "quota", "0", "default"],
                ["foo", "used", "9741332480", "-"],
                ["foo", "available", "468744720384", "-"],
                ["foo", "mountpoint", "/mnt/foo", "default"],
                ["foo", "type", "filesystem", "-"],
                ["foo/bar", "baz", "name", "foo/bar", "-"],
                ["foo/bar", "baz", "quota", "0", "default"],
                ["foo/bar", "baz", "used", "2060898304", "-"],
                ["foo/bar", "baz", "available", "468744720384", "-"],
                ["foo/bar", "baz", "mountpoint", "/mnt/foo/bar", "default"],
                ["foo/bar", "baz", "type", "filesystem", "-"],
                ["[df]"],
                ["/", "10255636", "1836517", "8419119", "18%", "/"],
                ["/dev", "10255636", "1836517", "8419119", "18%", "/dev"],
                ["foo", "zfs", "457758604", "88", "457758516", "0%", "/mnt/foo"],
                ["foo/bar", "zfs", "45977", "2012596", "457758516", "0%", "/mnt/foo/bar"],
            ],
            [("/mnt/foo", {}), ("/mnt/foo/bar", {}), ("/", {})],
        ),
        # separator: tab
        # no whitespace in device-names/mountpoints
        (
            [
                ["foo", "name", "foo", "-"],
                ["foo", "quota", "0", "default"],
                ["foo", "used", "9741332480", "-"],
                ["foo", "available", "468744720384", "-"],
                ["foo", "mountpoint", "/mnt/foo", "default"],
                ["foo", "type", "filesystem", "-"],
                ["foo/bar-baz", "name", "foo/bar-baz", "-"],
                ["foo/bar-baz", "quota", "0", "default"],
                ["foo/bar-baz", "used", "2060898304", "-"],
                ["foo/bar-baz", "available", "468744720384", "-"],
                ["foo/bar-baz", "mountpoint", "/mnt/foo/bar-baz", "default"],
                ["foo/bar-baz", "type", "filesystem", "-"],
                ["[df]"],
                ["/                    10255636 1836517 8419119    18%    /"],
                ["/dev                 10255636 1836517 8419119    18%    /dev"],
                ["foo                       457758604      88  457758516     0%    /mnt/foo"],
                ["foo/bar-baz              45977 2012596  457758516     0%    /mnt/foo/bar-baz"],
            ],
            [("/mnt/foo/bar-baz", {}), ("/mnt/foo", {}), ("/", {})],
        ),
        # separator: tab
        # no whitespace in device-names/mountpoints + FS_TYPE
        (
            [
                ["[zfs]"],
                ["foo", "name", "foo", "-"],
                ["foo", "quota", "0", "default"],
                ["foo", "used", "9741332480", "-"],
                ["foo", "available", "468744720384", "-"],
                ["foo", "mountpoint", "/mnt/foo", "default"],
                ["foo", "type", "filesystem", "-"],
                ["foo/bar-baz", "name", "foo/bar-baz", "-"],
                ["foo/bar-baz", "quota", "0", "default"],
                ["foo/bar-baz", "used", "2060898304", "-"],
                ["foo/bar-baz", "available", "468744720384", "-"],
                ["foo/bar-baz", "mountpoint", "/mnt/foo/bar-baz", "default"],
                ["foo/bar-baz", "type", "filesystem", "-"],
                ["[df]"],
                ["/                    10255636 1836517 8419119    18%    /"],
                ["/dev                 10255636 1836517 8419119    18%    /dev"],
                ["foo           zfs         457758604      88  457758516     0%    /mnt/foo"],
                ["foo/bar-baz   zfs        45977 2012596  457758516     0%    /mnt/foo/bar-baz"],
            ],
            [("/mnt/foo/bar-baz", {}), ("/mnt/foo", {}), ("/", {})],
        ),
        # separator: tab
        # with whitespace in device-names/mountpoints
        (
            [
                ["[zfs]"],
                ["f oo", "name", "f oo", "-"],
                ["f oo", "quota", "0", "default"],
                ["f oo", "used", "9741332480", "-"],
                ["f oo", "available", "468744720384", "-"],
                ["f oo", "mountpoint", "/mnt/f oo", "default"],
                ["f oo", "type", "filesystem", "-"],
                ["f oo/bar baz", "name", "f oo/bar baz", "-"],
                ["f oo/bar baz", "quota", "0", "default"],
                ["f oo/bar baz", "used", "2060898304", "-"],
                ["f oo/bar baz", "available", "468744720384", "-"],
                ["f oo/bar baz", "mountpoint", "/mnt/f oo/bar baz", "default"],
                ["f oo/bar baz", "type", "filesystem", "-"],
                ["[df]"],
                ["/                    10255636 1836517 8419119    18%    /"],
                ["/dev                 10255636 1836517 8419119    18%    /dev"],
                ["f oo                       457758604      88  457758516     0%    /mnt/f oo"],
                ["f oo/bar baz              45977 2012596  457758516     0%    /mnt/f oo/bar baz"],
            ],
            [("/mnt/f oo/bar baz", {}), ("/mnt/f oo", {}), ("/", {})],
        ),
        # separator zfs: tab
        # separator df: whitespace
        # with whitespace in device-names/mountpoints
        (
            [
                ["[zfs]"],
                ["f", "oo", "name", "f", "oo", "-"],
                ["f", "oo", "quota", "0", "default"],
                ["f", "oo", "used", "9741332480", "-"],
                ["f", "oo", "available", "468744720384", "-"],
                ["f", "oo", "mountpoint", "/mnt/f", "oo", "default"],
                ["f", "oo", "type", "filesystem", "-"],
                ["f", "oo/bar", "baz", "name", "f", "oo/bar", "baz", "-"],
                ["f", "oo/bar", "baz", "quota", "0", "default"],
                ["f", "oo/bar", "baz", "used", "2060898304", "-"],
                ["f", "oo/bar", "baz", "available", "468744720384", "-"],
                ["f", "oo/bar", "baz", "mountpoint", "/mnt/f", "oo/bar", "baz", "default"],
                ["f", "oo/bar", "baz", "type", "filesystem", "-"],
                ["[df]"],
                ["/", "10255636", "1836517", "8419119", "18%", "/"],
                ["/dev", "10255636", "1836517", "8419119", "18%", "/dev"],
                ["f", "oo", "457758604", "88", "457758516", "0%", "/mnt/f", "oo"],
                [
                    "f",
                    "oo/bar",
                    "baz",
                    "45977",
                    "2012596",
                    "457758516",
                    "0%",
                    "/mnt/f",
                    "oo/bar",
                    "baz",
                ],
            ],
            [("/mnt/f oo/bar baz", {}), ("/mnt/f oo", {}), ("/", {})],
        ),
        # separator zfs: tab
        # separator df: whitespace
        # with whitespace in device-names/mountpoints + FS_TYPE
        (
            [
                ["[zfs]"],
                ["f", "oo", "name", "f", "oo", "-"],
                ["f", "oo", "quota", "0", "default"],
                ["f", "oo", "used", "9741332480", "-"],
                ["f", "oo", "available", "468744720384", "-"],
                ["f", "oo", "mountpoint", "/mnt/f", "oo", "default"],
                ["f", "oo", "type", "filesystem", "-"],
                ["f", "oo/bar", "baz", "name", "f", "oo/bar", "baz", "-"],
                ["f", "oo/bar", "baz", "quota", "0", "default"],
                ["f", "oo/bar", "baz", "used", "2060898304", "-"],
                ["f", "oo/bar", "baz", "available", "468744720384", "-"],
                ["f", "oo/bar", "baz", "mountpoint", "/mnt/f", "oo/bar", "baz", "default"],
                ["f", "oo/bar", "baz", "type", "filesystem", "-"],
                ["[df]"],
                ["/", "10255636", "1836517", "8419119", "18%", "/"],
                ["/dev", "10255636", "1836517", "8419119", "18%", "/dev"],
                ["f", "oo", "zfs", "457758604", "88", "457758516", "0%", "/mnt/f", "oo"],
                [
                    "f",
                    "oo/bar",
                    "baz",
                    "zfs",
                    "45977",
                    "2012596",
                    "457758516",
                    "0%",
                    "/mnt/f",
                    "oo/bar",
                    "baz",
                ],
            ],
            [("/mnt/f oo/bar baz", {}), ("/mnt/f oo", {}), ("/", {})],
        ),
    ],
)
def test_zfsget_discovery(info, expected_discovery_result) -> None:
    check_zfsget = Check("zfsget")
    discovery_result = DiscoveryResult(check_zfsget.run_discovery(check_zfsget.run_parse(info)))
    assertDiscoveryResultsEqual(
        "zfsget", discovery_result, DiscoveryResult(expected_discovery_result)
    )
