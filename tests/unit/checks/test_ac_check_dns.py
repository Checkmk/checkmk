#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import ActiveCheck


@pytest.mark.parametrize(
    "params, result",
    [
        (("DESCR", {}), ["-H", "DESCR", "-s", "$HOSTADDRESS$", "-L"]),
        (
            (
                "DESCR",
                {
                    "expected_addresses_list": ["1.2.3.4", "5.6.7.8"],
                },
            ),
            ["-H", "DESCR", "-s", "$HOSTADDRESS$", "-L", "-a", "1.2.3.4", "-a", "5.6.7.8"],
        ),
        (
            (
                "DESCR",
                {
                    "expect_all_addresses": True,
                    "expected_addresses_list": ["5.6.7.8", "1.2.3.4"],
                },
            ),
            ["-H", "DESCR", "-s", "$HOSTADDRESS$", "-L", "-a", "5.6.7.8", "-a", "1.2.3.4"],
        ),
        (
            (
                "DESCR",
                {
                    "expect_all_addresses": False,
                    "expected_addresses_list": ["1.2.3.4", "5.6.7.8"],
                },
            ),
            ["-H", "DESCR", "-s", "$HOSTADDRESS$", "-a", "1.2.3.4", "-a", "5.6.7.8"],
        ),
    ],
)
def test_ac_check_dns_expected_addresses(params, result):
    active_check = ActiveCheck("check_dns")
    assert active_check.run_argument_function(params) == result
