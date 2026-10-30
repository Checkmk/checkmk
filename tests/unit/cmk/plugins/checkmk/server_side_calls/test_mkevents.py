#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.checkmk.server_side_calls.mkevents import active_check_mkevents
from cmk.server_side_calls.v1 import HostConfig


@pytest.mark.parametrize(
    "params,expected_args",
    [
        pytest.param(
            {"hostspec": ["$HOSTNAME$", "$HOSTADDRESS$"], "show_last_log": "details"},
            ["-L", "-q", "--", "hostname/ipaddress"],
            id="host list with the last log in the details",
        ),
        pytest.param(
            {"hostspec": ["$HOSTNAME$", "$HOSTALIAS$"], "show_last_log": "no"},
            ["-q", "--", "hostname/Router A\\/B\\\\C"],
            id="host list quoting slashes and backslashes",
        ),
        pytest.param(
            {"hostspec": "foobar", "show_last_log": "no"},
            ["--", "foobar"],
            id="host",
        ),
        pytest.param(
            {"hostspec": "foobar", "show_last_log": "no", "application": "-app"},
            ["--", "foobar", "-app"],
            id="application after the end of the options",
        ),
        pytest.param(
            {"hostspec": "foobar", "show_last_log": "no", "remote": ("myhost:6559", 6558)},
            ["-H", "myhost:6559", "--", "foobar"],
            id="remote host with its own port",
        ),
        pytest.param(
            {"hostspec": "foobar", "show_last_log": "no", "remote": (" myhost : 6559 ", 6558)},
            ["-H", "myhost:6559", "--", "foobar"],
            id="remote host with whitespace around its port",
        ),
        pytest.param(
            {"hostspec": "foobar", "show_last_log": "no", "remote": ("myhost:", 6559)},
            ["-H", "myhost:6559", "--", "foobar"],
            id="remote host with an empty port",
        ),
        pytest.param(
            {"hostspec": "foobar", "show_last_log": "no", "remote": ("myhost::6559", 6558)},
            ["-H", "myhost:6559", "--", "foobar"],
            id="remote host with its own port after colons",
        ),
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
            macros={
                "$HOSTNAME$": "hostname",
                "$HOSTADDRESS$": "ipaddress",
                "$HOSTALIAS$": "Router A/B\\C",
            },
        ),
    )
    assert command.command_arguments == expected_args
