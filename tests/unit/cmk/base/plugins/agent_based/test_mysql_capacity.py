#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Optional

import pytest

from cmk.base.api.agent_based.checking_classes import Metric, Result, Service, State
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based import mysql_capacity


@pytest.mark.parametrize(
    "sub_section, instance_name",
    [
        pytest.param(None, "mysql", id="default instance"),
        pytest.param("[[]]", "mysql", id="empty instance"),
        pytest.param("[[cmk]]", "cmk", id="named instance"),
    ],
)
def test_parse(sub_section: Optional[str], instance_name: str) -> None:
    args: StringTable = [
        ["greendb", "163840", "1428160512"],
    ]
    if sub_section is not None:
        args = [
            [
                sub_section,
            ],
            args[0],
        ]
    expected = {instance_name: {"greendb": 163840}}
    assert mysql_capacity.parse_size(args) == expected


def test_parse_empty_instance_default_to_previous() -> None:
    args = [
        ["[[some]]"],
        ["greendb", "163840", "1428160512"],
        ["[[]]"],
        ["reddb", "163840", "1428160512"],
    ]
    expected = {
        "some": {
            "greendb": 163840,
            "reddb": 163840,
        }
    }
    assert mysql_capacity.parse_size(args) == expected


def test_parse_exclude_non_int_size_info() -> None:
    args = [
        ["greendb", "1dd63840", "1428160512"],
    ]
    expected: dict[str, dict[str, int]] = {}
    assert mysql_capacity.parse_size(args) == expected


def test_discovery() -> None:
    section = {
        "mysql": {
            "red": 12,
            "information_schema": 12,
            "performance_schema": 12,
            "mysql": 12,
        }
    }
    assert list(mysql_capacity.discover_capacity(section)) == [Service(item="mysql:red")]


def test_check() -> None:
    item = "mysql:reddb"
    params = {"levels": (None, None)}
    section = {"mysql": {"reddb": 42}}

    assert list(mysql_capacity.check_capacity(item, params, section)) == [
        Result(state=State.OK, summary="Size: 42 B"),
        Metric("database_size", 42.0),
    ]
