#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State, StringTable
from cmk.plugins.podman.agent_based.podman_status import (
    check_podman_status,
    discover_podman_status,
    parse_podman_status,
)

STRING_TABLE = [
    [
        '{"endpoint": "/run/user/999/podman/podman.sock/v4.0.0/libpod/containers/json", "message": "(\'Connection aborted.\', ConnectionRefusedError(111, \'Connection refused\'))"}'
    ],
    [
        '{"endpoint": "/run/user/999/podman/podman.sock/v4.0.0/libpod/system/df", "message": "(\'Connection aborted.\', ConnectionRefusedError(111, \'Connection refused\'))"}'
    ],
    [
        '{"endpoint": "/run/user/999/podman/podman.sock/v4.0.0/libpod/info", "message": "(\'Connection aborted.\', ConnectionRefusedError(111, \'Connection refused\'))"}'
    ],
    [
        '{"endpoint": "/run/user/999/podman/podman.sock/v4.0.0/libpod/pods/json", "message": "(\'Connection aborted.\', ConnectionRefusedError(111, \'Connection refused\'))"}'
    ],
    [
        '{"endpoint": "/run/user/999/podman/podman.sock/v4.0.0/libpod/containers/json", "message": "(\'Connection aborted.\', ConnectionRefusedError(111, \'Connection refused\'))"}'
    ],
]

NO_ERRORS_STRING_TABLE = [["{}"]]


def test_discover_podman_status() -> None:
    assert list(discover_podman_status(parse_podman_status(STRING_TABLE))) == [Service()]
    assert list(discover_podman_status(parse_podman_status(NO_ERRORS_STRING_TABLE))) == [Service()]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            NO_ERRORS_STRING_TABLE,
            [Result(state=State.OK, summary="No errors")],
            id="No Errors present -> OK",
        ),
        pytest.param(
            STRING_TABLE,
            [
                Result(
                    state=State.CRIT,
                    summary="Errors: 5, see details",
                    details="/run/user/999/podman/podman.sock/v4.0.0/libpod/containers/json: ('Connection aborted.', ConnectionRefusedError(111, 'Connection refused'))\n/run/user/999/podman/podman.sock/v4.0.0/libpod/system/df: ('Connection aborted.', ConnectionRefusedError(111, 'Connection refused'))\n/run/user/999/podman/podman.sock/v4.0.0/libpod/info: ('Connection aborted.', ConnectionRefusedError(111, 'Connection refused'))\n/run/user/999/podman/podman.sock/v4.0.0/libpod/pods/json: ('Connection aborted.', ConnectionRefusedError(111, 'Connection refused'))\n/run/user/999/podman/podman.sock/v4.0.0/libpod/containers/json: ('Connection aborted.', ConnectionRefusedError(111, 'Connection refused'))",
                ),
            ],
            id="Errors present -> CRIT",
        ),
    ],
)
def test_check_podman_status(string_table: StringTable, expected_result: CheckResult) -> None:
    assert list(check_podman_status(parse_podman_status(string_table))) == expected_result
