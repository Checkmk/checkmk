#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import nullcontext
from enum import auto, StrEnum

import pytest

import cmk.gui.valuespec as vs
from cmk.gui.exceptions import MKUserError


class ValueType(StrEnum):
    name_ = auto()
    ipv4 = auto()
    ipv6 = auto()
    none = auto()


@pytest.mark.parametrize(
    "allow_host_name", (True, False), ids=["allow_host_name", "not allow_host_name"]
)
@pytest.mark.parametrize(
    "allow_ipv4_address", (True, False), ids=["allow_ipv4_address", "not allow_ipv4_address"]
)
@pytest.mark.parametrize(
    "allow_ipv6_address", (True, False), ids=["allow_ipv6_address", "not allow_ipv6_address"]
)
@pytest.mark.parametrize(
    "value_type,value",
    [
        (ValueType.name_, "xyz"),
        (ValueType.name_, "xyz001_d3"),
        (ValueType.name_, "abc-def-ghi"),
        (ValueType.name_, "asd.abc"),
        (ValueType.name_, "asd.abc."),
        (ValueType.ipv4, "10.10.123.234"),
        (ValueType.ipv4, "10.10.123.234"),
        (ValueType.ipv6, "2001:db8:3333:4444:5555:6666:7777:8888"),
        (ValueType.ipv6, "::1234:5678"),
        (ValueType.none, "999.10.123.234"),
        (ValueType.none, "::&a:5678"),
        (ValueType.none, "/asd/eee"),
        (ValueType.none, "e/d/f"),
        (ValueType.none, "a/../e"),
        (ValueType.none, "-ding"),
        (ValueType.none, "dong-"),
        (ValueType.none, "01234567"),
        (ValueType.none, "012.345.67"),
        (ValueType.none, "127.1"),
        (ValueType.none, "a" * 256 + ".com"),
        (ValueType.none, ""),
    ],
)
def test_host_address_validate_value(
    value_type: ValueType,
    value: str,
    allow_host_name: bool,
    allow_ipv4_address: bool,
    allow_ipv6_address: bool,
) -> None:
    expected_valid = (
        (value_type is ValueType.name_ and allow_host_name)
        or (value_type is ValueType.ipv4 and allow_ipv4_address)
        or (value_type is ValueType.ipv6 and allow_ipv6_address)
    )
    with pytest.raises(MKUserError) if not expected_valid else nullcontext():
        vs.HostAddress(
            allow_host_name=allow_host_name,
            allow_ipv4_address=allow_ipv4_address,
            allow_ipv6_address=allow_ipv6_address,
            allow_empty=False,
        ).validate_value(value, "varprefix")
