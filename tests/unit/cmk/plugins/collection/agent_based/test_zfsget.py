#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Service, StringTable
from cmk.plugins.collection.agent_based import zfsget


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
                "/mnt/dataset13": ("/mnt/dataset13", 43182749.63244629, 11311624.923248291, 0.0),
                "/mnt/dataset13/MyFolder": ("/mnt/dataset13/MyFolder", 5242880.0, 0.0, 0.0),
            },
        ),
    ],
)
def test_zfsget_parse(info: StringTable, expected_parse_result: zfsget.Section) -> None:
    assert zfsget.parse_zfsget(info) == expected_parse_result


@pytest.mark.parametrize(
    "info,expected_discovery_result",
    [
        pytest.param([], [], id="empty"),
        pytest.param(
            [
                ["[zfs]"],
                ["[df]"],
            ],
            [],
            id="no zfsget items and no df item",
        ),
        pytest.param(
            [
                ["[zfs]"],
                ["[df]"],
                ["/", "10255636", "1836517", "8419119", "18%", "/"],
                ["/dev", "10255636", "1836517", "8419119", "18%", "/dev"],
                ["foo", "zfs", "457758604", "88", "457758516", "0%", "/mnt/foo"],
                ["foo/bar", "zfs", "45977", "2012596", "457758516", "0%", "/mnt/foo/bar"],
            ],
            [("/mnt/foo", {}), ("/mnt/foo/bar", {}), ("/", {})],
            id="separator df: whitespace, no zfsget items and pass-through filesystem",
        ),
        pytest.param(
            [
                ["[zfs]"],
                ["[df]"],
                ["/", "10255636", "1836517", "8419119", "18%", "/"],
                ["/dev", "10255636", "1836517", "8419119", "18%", "/dev"],
            ],
            [("/", {})],
            id="separator df: whitespace, no zfsget items and pass-through filesystem",
        ),
        pytest.param(
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
            id=(
                "separator zfs: tab, "
                "separator df: whitespace, "
                "no whitespace in device-names/mountpoints"
            ),
        ),
        pytest.param(
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
            id=(
                "separator zfs: tab, "
                "separator df: whitespace, "
                "no whitespace in device-names/mountpoints + FS_TYPE"
            ),
        ),
        pytest.param(
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
            id="separator: tab, no whitespace in device-names/mountpoints",
        ),
        pytest.param(
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
            id="separator: tab, no whitespace in device-names/mountpoints + FS_TYPE",
        ),
        pytest.param(
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
            id="separator: tab, with whitespace in device-names/mountpoints",
        ),
        pytest.param(
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
            id=(
                "separator zfs: tab, "
                "separator df: whitespace, "
                "with whitespace in device-names/mountpoints"
            ),
        ),
        pytest.param(
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
            id=(
                "separator zfs: tab, "
                "separator df: whitespace, "
                "with whitespace in device-names/mountpoints + FS_TYPE"
            ),
        ),
    ],
)
def test_zfsget_discovery(
    info: StringTable, expected_discovery_result: Sequence[tuple[str, Mapping[str, object]]]
) -> None:
    assert sorted(zfsget.discover_zfsget([{"groups": []}], zfsget.parse_zfsget(info))) == sorted(
        Service(item=i, parameters=p) for i, p in expected_discovery_result
    )


STRING_TABLE_WHITESPACES = [
    ["DataStorage", "name", "DataStorage", "-"],
    ["DataStorage", "quota", "0", "default"],
    ["DataStorage", "used", "7560117312", "-"],
    ["DataStorage", "available", "3849844262352", "-"],
    ["DataStorage", "mountpoint", "/mnt/DataStorage", "default"],
    ["DataStorage", "type", "filesystem", "-"],
    ["DataStorage/ ISO-File ", "name", "DataStorage/ ISO-File ", "-"],
    ["DataStorage/ ISO-File ", "quota", "0", "default"],
    ["DataStorage/ ISO-File ", "used", "180048", "-"],
    ["DataStorage/ ISO-File ", "available", "3849844262352", "-"],
    ["DataStorage/ ISO-File ", "mountpoint", "/mnt/DataStorage/ ISO-File ", "default"],
    ["DataStorage/ ISO-File ", "type", "filesystem", "-"],
    ["DataStorage/Server1a", "name", "DataStorage/Server1a", "-"],
    ["DataStorage/Server1a", "quota", "0", "default"],
    ["DataStorage/Server1a", "used", "7558161336", "-"],
    ["DataStorage/Server1a", "available", "3849844262352", "-"],
    ["DataStorage/Server1a", "mountpoint", "/mnt/DataStorage/Server1a", "default"],
    ["DataStorage/Server1a", "type", "filesystem", "-"],
    ["freenas-boot", "name", "freenas-boot", "-"],
    ["freenas-boot", "quota", "0", "default"],
    ["freenas-boot", "used", "800454656", "-"],
    ["freenas-boot", "available", "28844803072", "-"],
    ["freenas-boot", "mountpoint", "none", "local"],
    ["freenas-boot", "type", "filesystem", "-"],
    ["freenas-boot/ROOT", "name", "freenas-boot/ROOT", "-"],
    ["freenas-boot/ROOT", "quota", "0", "default"],
    ["freenas-boot/ROOT", "used", "799748608", "-"],
    ["freenas-boot/ROOT", "available", "28844803072", "-"],
    ["freenas-boot/ROOT", "mountpoint", "none", "inherited from freenas-boot"],
    ["freenas-boot/ROOT", "type", "filesystem", "-"],
    ["freenas-boot/ROOT/Initial-Install", "name", "freenas-boot/ROOT/Initial-Install", "-"],
    ["freenas-boot/ROOT/Initial-Install", "quota", "0", "default"],
    ["freenas-boot/ROOT/Initial-Install", "used", "1024", "-"],
    ["freenas-boot/ROOT/Initial-Install", "available", "28844803072", "-"],
    ["freenas-boot/ROOT/Initial-Install", "mountpoint", "legacy", "local"],
    ["freenas-boot/ROOT/Initial-Install", "type", "filesystem", "-"],
    ["freenas-boot/ROOT/default", "name", "freenas-boot/ROOT/default", "-"],
    ["freenas-boot/ROOT/default", "quota", "0", "default"],
    ["freenas-boot/ROOT/default", "used", "799717888", "-"],
    ["freenas-boot/ROOT/default", "available", "28844803072", "-"],
    ["freenas-boot/ROOT/default", "mountpoint", "legacy", "local"],
    ["freenas-boot/ROOT/default", "type", "filesystem", "-"],
    ["test2", "name", "test2", "-"],
    ["test2", "quota", "0", "default"],
    ["test2", "used", "9741332480", "-"],
    ["test2", "available", "468744720384", "-"],
    ["test2", "mountpoint", "/mnt/test2", "default"],
    ["test2", "type", "filesystem", "-"],
    ["test2/ISO-File", "name", "test2/ISO-File", "-"],
    ["test2/ISO-File", "quota", "0", "default"],
    ["test2/ISO-File", "used", "2060898304", "-"],
    ["test2/ISO-File", "available", "468744720384", "-"],
    ["test2/ISO-File", "mountpoint", "/mnt/test2/ISO-File", "default"],
    ["test2/ISO-File", "type", "filesystem", "-"],
    ["test2/Server1", "name", "test2/Server1", "-"],
    ["test2/Server1", "quota", "0", "default"],
    ["test2/Server1", "used", "7675715584", "-"],
    ["test2/Server1", "available", "468744720384", "-"],
    ["test2/Server1", "mountpoint", "/mnt/test2/Server1", "default"],
    ["test2/Server1", "type", "filesystem", "-"],
    ["test2/iocage", "name", "test2/iocage", "-"],
    ["test2/iocage", "quota", "0", "default"],
    ["test2/iocage", "used", "647168", "-"],
    ["test2/iocage", "available", "468744720384", "-"],
    ["test2/iocage", "mountpoint", "/mnt/test2/iocage", "default"],
    ["test2/iocage", "type", "filesystem", "-"],
    ["test2/iocage/download", "name", "test2/iocage/download", "-"],
    ["test2/iocage/download", "quota", "0", "default"],
    ["test2/iocage/download", "used", "90112", "-"],
    ["test2/iocage/download", "available", "468744720384", "-"],
    ["test2/iocage/download", "mountpoint", "/mnt/test2/iocage/download", "default"],
    ["test2/iocage/download", "type", "filesystem", "-"],
    ["test2/iocage/images", "name", "test2/iocage/images", "-"],
    ["test2/iocage/images", "quota", "0", "default"],
    ["test2/iocage/images", "used", "90112", "-"],
    ["test2/iocage/images", "available", "468744720384", "-"],
    ["test2/iocage/images", "mountpoint", "/mnt/test2/iocage/images", "default"],
    ["test2/iocage/images", "type", "filesystem", "-"],
    ["test2/iocage/jails", "name", "test2/iocage/jails", "-"],
    ["test2/iocage/jails", "quota", "0", "default"],
    ["test2/iocage/jails", "used", "90112", "-"],
    ["test2/iocage/jails", "available", "468744720384", "-"],
    ["test2/iocage/jails", "mountpoint", "/mnt/test2/iocage/jails", "default"],
    ["test2/iocage/jails", "type", "filesystem", "-"],
    ["test2/iocage/log", "name", "test2/iocage/log", "-"],
    ["test2/iocage/log", "quota", "0", "default"],
    ["test2/iocage/log", "used", "90112", "-"],
    ["test2/iocage/log", "available", "468744720384", "-"],
    ["test2/iocage/log", "mountpoint", "/mnt/test2/iocage/log", "default"],
    ["test2/iocage/log", "type", "filesystem", "-"],
    ["test2/iocage/releases", "name", "test2/iocage/releases", "-"],
    ["test2/iocage/releases", "quota", "0", "default"],
    ["test2/iocage/releases", "used", "90112", "-"],
    ["test2/iocage/releases", "available", "468744720384", "-"],
    ["test2/iocage/releases", "mountpoint", "/mnt/test2/iocage/releases", "default"],
    ["test2/iocage/releases", "type", "filesystem", "-"],
    ["test2/iocage/templates", "name", "test2/iocage/templates", "-"],
    ["test2/iocage/templates", "quota", "0", "default"],
    ["test2/iocage/templates", "used", "90112", "-"],
    ["test2/iocage/templates", "available", "468744720384", "-"],
    ["test2/iocage/templates", "mountpoint", "/mnt/test2/iocage/templates", "default"],
    ["test2/iocage/templates", "type", "filesystem", "-"],
    ["[df]"],
    ["freenas-boot/ROOT/default    28942113  773360   28168753     3%    /"],
    ["test2                       457758604      88  457758516     0%    /mnt/test2"],
    ["test2/ISO-File              459771112 2012596  457758516     0%    /mnt/test2/ISO-File"],
    ["test2/Server1               465254332 7495816  457758516     2%    /mnt/test2/Server1"],
    ["test2/iocage                457758620     104  457758516     0%    /mnt/test2/iocage"],
    [
        "test2/iocage/download       457758604      88  457758516     0%    /mnt/test2/iocage/download"
    ],
    ["test2/iocage/images         457758604      88  457758516     0%    /mnt/test2/iocage/images"],
    ["test2/iocage/jails          457758604      88  457758516     0%    /mnt/test2/iocage/jails"],
    ["test2/iocage/log            457758604      88  457758516     0%    /mnt/test2/iocage/log"],
    [
        "test2/iocage/releases       457758604      88  457758516     0%    /mnt/test2/iocage/releases"
    ],
    [
        "test2/iocage/templates      457758604      88  457758516     0%    /mnt/test2/iocage/templates"
    ],
    ["DataStorage                3759613713     176 3759613537     0%    /mnt/DataStorage"],
    [
        "DataStorage/ ISO-File      3759613713     176 3759613537     0%    /mnt/DataStorage/ ISO-File"
    ],
    [
        "DataStorage/Server1a       3766994554 7381017 3759613537     0%    /mnt/DataStorage/Server1a"
    ],
]


def test_discovery_string_table_ws() -> None:
    assert sorted(
        zfsget.discover_zfsget([{"groups": []}], zfsget.parse_zfsget(STRING_TABLE_WHITESPACES))
    ) == sorted(
        [
            Service(item="/", parameters={}),
            Service(item="/mnt/DataStorage", parameters={}),
            Service(item="/mnt/DataStorage/ ISO-File", parameters={}),
            Service(item="/mnt/DataStorage/Server1a", parameters={}),
            Service(item="/mnt/test2", parameters={}),
            Service(item="/mnt/test2/ISO-File", parameters={}),
            Service(item="/mnt/test2/Server1", parameters={}),
            Service(item="/mnt/test2/iocage", parameters={}),
            Service(item="/mnt/test2/iocage/download", parameters={}),
            Service(item="/mnt/test2/iocage/images", parameters={}),
            Service(item="/mnt/test2/iocage/jails", parameters={}),
            Service(item="/mnt/test2/iocage/log", parameters={}),
            Service(item="/mnt/test2/iocage/releases", parameters={}),
            Service(item="/mnt/test2/iocage/templates", parameters={}),
        ]
    )
