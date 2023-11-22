#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.testlib import ActiveCheck

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        pytest.param(
            {},
            ["$HOSTADDRESS$"],
            id="minimal configuration",
        ),
        pytest.param(
            {
                "description": "abc",
                "port": 4587,
                "timeout": 120,
                "remote_version": "OpenSSH_8.2p1",
                "remote_protocol": "2.0",
            },
            [
                "-t",
                120,
                "-p",
                4587,
                "-r",
                "OpenSSH_8.2p1",
                "-P",
                "2.0",
                "$HOSTADDRESS$",
            ],
            id="full configuration",
        ),
    ],
)
def test_check_ssh_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[str]
) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_ssh")
    assert active_check.run_argument_function(params) == expected_args
