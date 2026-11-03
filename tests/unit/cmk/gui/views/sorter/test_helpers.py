#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.gui.views.sorter.helpers import (
    cmp_insensitive_string,
    cmp_ip_address,
    cmp_num_split,
    cmp_simple_number,
    cmp_simple_string,
    cmp_string_list,
    compare_ips,
)


# fmt: off
@pytest.mark.parametrize(
    "ip1, ip2, ipv, expected",
    [
        pytest.param("10.0.0.9", "10.0.0.10", "ipv4", -1, id="IPv4 compares numerically"),
        pytest.param("my-host", "10.0.0.10", "ipv4", 1, id="IPv4 sorts host names last"),
        pytest.param("", "fe80::1", "ipv6", 1, id="IPv6 sorts a missing address last"),
    ],
)
# fmt: on
def test_addresses_sort_in_network_order(
    ip1: str, ip2: str, ipv: Literal["ipv4", "ipv6"], expected: int
) -> None:
    assert compare_ips(ip1, ip2, ipv) == expected


def test_a_missing_address_column_sorts_like_an_empty_address() -> None:
    assert cmp_ip_address("host_address", {}, {"host_address": "10.0.0.1"}) == 1


def test_numbers_compare_by_value() -> None:
    assert cmp_simple_number("service_state", {"service_state": 2}, {"service_state": 10}) == -1


def test_names_with_numbers_compare_by_the_numbers_they_contain() -> None:
    assert cmp_num_split("host_name", {"host_name": "Node10"}, {"host_name": "node9"}) == 1


def test_strings_compare_case_insensitively_first() -> None:
    assert cmp_simple_string("host_name", {"host_name": "alpha"}, {"host_name": "Beta"}) == -1


def test_strings_differing_only_in_case_still_get_a_strict_order() -> None:
    assert cmp_insensitive_string("Alpha", "alpha") == -1


def test_string_lists_compare_by_their_joined_content() -> None:
    assert cmp_string_list("host_groups", {"host_groups": ["a", "b"]}, {}) == 1
