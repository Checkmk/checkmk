#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import ActiveCheck

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {"port": 123, "service": "foobar", "job": "version"},
            ["$HOSTADDRESS$", 123, "foobar", "VERSION"],
        ),
        (
            {
                "port": 123,
                "service": "foobar",
                "job": (
                    "address",
                    {"street": "street", "street_no": 0, "city": "city", "search_regex": "regex"},
                ),
            },
            ["$HOSTADDRESS$", 123, "foobar", "ADDRESS", "street", 0, "city", "regex"],
        ),
    ],
)
def test_check_uniserv_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_uniserv")
    assert active_check.run_argument_function(params) == expected_args
