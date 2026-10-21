#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.modes.check_mk import fake_dns_address, state_exit_code
from cmk.ccc.exceptions import MKBailOut
from cmk.ccc.hostaddress import HostAddress
from cmk.cli.internal import ExitCode


def test_no_fake_dns_option_leaves_the_lookup_alone() -> None:
    assert fake_dns_address({}) is None


def test_the_fake_dns_option_is_a_host_address() -> None:
    assert fake_dns_address({"fake-dns": "1.2.3.4"}) == HostAddress("1.2.3.4")


def test_an_invalid_fake_dns_address_is_refused() -> None:
    with pytest.raises(MKBailOut):
        fake_dns_address({"fake-dns": "not an address!"})


@pytest.mark.parametrize(
    ["state", "expected"],
    [
        (0, ExitCode.SUCCESS),
        (1, ExitCode.FAILURE),
        (2, ExitCode.ERROR),
        (3, ExitCode.UNKNOWN),
        (4, ExitCode.UNKNOWN),
        (-1, ExitCode.UNKNOWN),
        (127, ExitCode.UNKNOWN),
    ],
)
def test_a_state_exits_with_its_monitoring_meaning(state: int, expected: ExitCode) -> None:
    assert state_exit_code(state) == expected
