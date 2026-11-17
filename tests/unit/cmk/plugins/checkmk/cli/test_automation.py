#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shlex
from collections.abc import Mapping, Sequence

import pytest

from cmk.automations.backends import SubprocessExecutor
from cmk.automations.internal import AutomationID
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.automation import (
    _automation_request,
    _FOR_CMK_VERSION_VALUE,
    AutomationRequest,
)


def test_a_subprocess_automation_passes_the_version_as_the_command_declares_it() -> None:
    argv = shlex.split(
        SubprocessExecutor().command_description(
            AutomationID("service-discovery-preview"),
            ["myhost"],
            None,
            for_cmk_version="2.4.0p1",
        )
    )

    assert argv[argv.index(f"--{_FOR_CMK_VERSION_VALUE.long}") + 1] == "2.4.0p1"


def test_the_automation_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        _FOR_CMK_VERSION_VALUE: ["2.4.0p1"],
        CLIArguments(placeholder="COMMAND...", parse=str): ["service-discovery-preview", "myhost"],
    }

    assert _automation_request(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == AutomationRequest(
        for_cmk_version="2.4.0p1", arguments=("service-discovery-preview", "myhost")
    )


def test_an_invalid_version_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid version string"):
        given: Mapping[CLIDeclaration, Sequence[str]] = {_FOR_CMK_VERSION_VALUE: ["foo"]}

        _automation_request(CLIReader(lambda declaration: given.get(declaration, ())))
