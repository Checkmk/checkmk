#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import shlex

import pytest

from cmk.automations.backends import SubprocessExecutor
from cmk.automations.engine import AutomationError
from cmk.automations.internal import AutomationID
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.engine.readers import RecordedOptions as CLIRecordedOptions
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.plugins.checkmk.cli.automation import (
    _automation_error_exit_code,
    _for_cmk_version_request,
    _FOR_CMK_VERSION_VALUE,
    cli_command_automation,
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


def test_automation_declares_the_version_option_alone() -> None:
    recorded = CLIRecordedOptions()
    cli_command_automation.request(recorded)

    assert [option.long for option in recorded.options] == ["for-cmk-version"]


def test_the_requested_version_is_read_from_the_command_line() -> None:
    options = CLIParsedOptions([("--for-cmk-version", "2.4.0p1")], logging.getLogger(__name__))

    assert _for_cmk_version_request(options) == "2.4.0p1"


def test_an_invalid_version_is_rejected() -> None:
    with pytest.raises(ValueError, match="--for-cmk-version: Invalid argument"):
        _for_cmk_version_request(
            CLIParsedOptions([("--for-cmk-version", "foo")], logging.getLogger(__name__))
        )


@pytest.mark.parametrize(
    ["error", "expected"],
    [
        (AutomationError.KNOWN_ERROR, CLIExitCode.FAILURE),
        (AutomationError.UNKNOWN_ERROR, CLIExitCode.ERROR),
    ],
)
def test_an_automation_error_exits_with_its_value(
    error: AutomationError, expected: CLIExitCode
) -> None:
    assert _automation_error_exit_code(error) == expected
