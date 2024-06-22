#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.collection.server_side_calls.mkevents import active_check_mkevents
from cmk.server_side_calls.v1 import HostConfig


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {"hostspec": ["$HOSTNAME$", "$HOSTADDRESS$"], "show_last_log": "details"},
            ["-L", "hostname/ipaddress"],
        ),
        ({"hostspec": "foobar", "show_last_log": "no"}, ["foobar"]),
    ],
)
def test_check_mkevents_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[str]
) -> None:
    """Tests if all required arguments are present."""
    (command,) = active_check_mkevents(
        params,
        HostConfig(
            name="hostname",
            macros={"$HOSTNAME$": "hostname", "$HOSTADDRESS$": "ipaddress"},
        ),
    )
    assert command.command_arguments == expected_args
