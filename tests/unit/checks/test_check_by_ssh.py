#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Mapping

import pytest

from cmk.plugins.ssh.server_side_calls.check_by_ssh import active_check_by_ssh
from cmk.server_side_calls.v1 import HostConfig, IPAddressFamily

pytestmark = pytest.mark.checks

TEST_HOST_CONFIG = HostConfig(
    "my_host", "1.2.3.4", "my_alias", IPAddressFamily.IPV4, ipv4address="my.ipv4.address"
)


@pytest.mark.parametrize(
    "params,expected_args",
    [
        ({"options": ("foo", {})}, ["-H", "1.2.3.4", "-C", "foo"]),
        ({"options": ("foo", {"port": 22})}, ["-H", "1.2.3.4", "-C", "foo", "-p", 22]),
    ],
)
def test_check_by_ssh_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[object]
) -> None:
    """Tests if all required arguments are present."""
    (cmd,) = active_check_by_ssh.commands_function(
        active_check_by_ssh.parameter_parser(params), TEST_HOST_CONFIG, {}
    )

    assert cmd.command_arguments == expected_args
