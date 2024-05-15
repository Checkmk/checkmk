#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from collections.abc import Mapping
from pathlib import Path

import pytest

from cmk.utils.hostaddress import HostName

from cmk.base.server_side_calls import SpecialAgentInfoFunctionResult
from cmk.base.server_side_calls._commons import ActiveCheckError, commandline_arguments


@pytest.mark.parametrize(
    "args, passwords, expected_result",
    [
        pytest.param("args 123 -x 1 -y 2", {}, "args 123 -x 1 -y 2", id="string argument"),
        pytest.param(
            ["args", "1; echo", "-x", "1", "-y", "2"],
            {},
            "args '1; echo' -x 1 -y 2",
            id="list argument",
        ),
        pytest.param(
            ["args", "1 2 3", "-d=2", "--hallo=eins", 9],
            {},
            "args '1 2 3' -d=2 --hallo=eins 9",
            id="list argument with numbers",
        ),
        pytest.param(
            ["arg1", ("store", "pw-id", "--password=%s"), "arg3"],
            {"pw-id": "aädg"},
            "--pwstore=2@11@/my/password/store@pw-id arg1 '--password=****' arg3",
            id="password store argument",
        ),
        pytest.param(
            ["arg1", ("store", "pw-id; echo HI;", "--password=%s"), "arg3"],
            {"pw-id; echo HI;": "the password"},
            "'--pwstore=2@11@/my/password/store@pw-id; echo HI;' arg1 '--password=************' arg3",
            id="password store sanitization (CMK-14149)",
        ),
    ],
)
def test_commandline_arguments(
    args: SpecialAgentInfoFunctionResult,
    passwords: Mapping[str, str],
    expected_result: str,
) -> None:
    cmdline_args = commandline_arguments(
        HostName("test"),
        "test service",
        args,
        passwords,
        Path("/my/password/store"),
    )
    assert cmdline_args == expected_result


@pytest.mark.parametrize(
    "host_name, service_name, expected_warning",
    [
        pytest.param(
            HostName("test"),
            "test service",
            'The stored password "pw-id" used by service "test service" on host "test" does not exist (anymore).',
            id="host and service names present",
        ),
        pytest.param(
            HostName("test"),
            None,
            'The stored password "pw-id" used by host "test" does not exist (anymore).',
            id="service name not present",
        ),
        pytest.param(
            None,
            None,
            'The stored password "pw-id" does not exist (anymore).',
            id="host and service names not present",
        ),
    ],
)
def test_commandline_arguments_nonexisting_password(
    host_name: HostName,
    service_name: str,
    expected_warning: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    commandline_arguments(
        host_name,
        service_name,
        ["arg1", ("store", "pw-id", "--password=%s"), "arg3"],
        {},
        Path("/pw/store"),
    )
    captured = capsys.readouterr()
    assert expected_warning in captured.out


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(None, id="None argument"),
        pytest.param(1, id="integer argument"),
        pytest.param((1, 2), id="integer tuple"),
    ],
)
def test_commandline_arguments_invalid_arguments_type(args: int | tuple[int, int] | None) -> None:
    with pytest.raises(
        ActiveCheckError,
        match=r"The check argument function needs to return either a list of arguments or a string of the concatenated arguments \(Service: test service\).",
    ):
        commandline_arguments(
            HostName("test"),
            "test service",
            args,  # type: ignore[arg-type]
            {},
            Path("/pw/store"),
        )


def test_commandline_arguments_invalid_argument() -> None:
    with pytest.raises(
        ActiveCheckError,
        match=r"Invalid argument for command line: \(1, 2\)",
    ):
        commandline_arguments(
            HostName("test"),
            "test service",
            ["arg1", (1, 2), "arg3"],  # type: ignore[list-item]
            {},
            Path("/pw/store"),
        )
