#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import ActiveCheck

pytestmark = pytest.mark.checks

STATIC_ARGS = ["--inventory-as-check", "$HOSTNAME$"]


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {},
            ["--inv-fail-status=1", "--hw-changes=0", "--sw-changes=0", "--sw-missing=0"]
            + STATIC_ARGS,
        ),
        (
            {"timeout": 0},
            ["--inv-fail-status=1", "--hw-changes=0", "--sw-changes=0", "--sw-missing=0"]
            + STATIC_ARGS,
        ),
    ],
)
def test_check_cmk_inv_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_cmk_inv")
    assert active_check.run_argument_function(params) == expected_args
