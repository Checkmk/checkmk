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
        (["foo", {}], ["-H", "foo", "-s", "$HOSTADDRESS$", "-L"]),
        (["foo", {"timeout": 1}], ["-H", "foo", "-s", "$HOSTADDRESS$", "-L", "-t", 1]),
    ],
)
def test_check_dns_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_dns")
    assert active_check.run_argument_function(params) == expected_args
