#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

import pytest

from cmk.utils.hostaddress import HostName

from cmk.server_side_calls_backend import SpecialAgentInfoFunctionResult
from cmk.server_side_calls_backend._commons import (
    ActiveCheckError,
    ExecutableFinder,
    legacy_commandline_arguments,
)


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
    cmdline_args = legacy_commandline_arguments(
        HostName("test"),
        args,
        passwords,
        Path("/my/password/store"),
    )
    assert cmdline_args == expected_result


def test_commandline_arguments_nonexisting_password(capsys: pytest.CaptureFixture[str]) -> None:
    legacy_commandline_arguments(
        HostName("test"),
        ["arg1", ("store", "pw-id", "--password=%s"), "arg3"],
        {},
        Path("/pw/store"),
    )
    assert (
        'The stored password "pw-id" used by host "test" does not exist (anymore).'
        in capsys.readouterr().out
    )


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
        match=r"The agent argument function needs to return either a list of arguments or a string of the concatenated arguments.",
    ):
        legacy_commandline_arguments(
            HostName("test"),
            args,  # type: ignore[arg-type]
            {},
            Path("/pw/store"),
        )


def test_commandline_arguments_invalid_argument() -> None:
    with pytest.raises(
        ActiveCheckError,
        match=r"Invalid argument for command line: \(1, 2\)",
    ):
        legacy_commandline_arguments(
            HostName("test"),
            ["arg1", (1, 2), "arg3"],  # type: ignore[list-item]
            {},
            Path("/pw/store"),
        )


@contextmanager
def _with_file(path: Path) -> Iterator[None]:
    present = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    try:
        yield
    finally:
        if not present:
            path.unlink(missing_ok=True)


def test_executable_finder_local(tmp_path: Path) -> None:
    binary_name = "execthis"
    shipped_file = tmp_path / "shipped" / binary_name
    local_file = tmp_path / "local" / binary_name
    finder = ExecutableFinder(local_file.parent, shipped_file.parent)

    with _with_file(shipped_file):
        assert finder(binary_name, None) == str(shipped_file)
        with _with_file(local_file):
            assert finder(binary_name, None) == str(local_file)
