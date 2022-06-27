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
            {"share": "foo", "levels": (85.0, 95.0)},
            ["-a", "$HOSTADDRESS$", "-s", "foo", "-w85%", "-c95%", "-H", "$HOSTADDRESS$"],
        ),
    ],
)
def test_check_disk_smb_argument_parsing(params, expected_args) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_disk_smb")
    assert active_check.run_argument_function(params) == expected_args
