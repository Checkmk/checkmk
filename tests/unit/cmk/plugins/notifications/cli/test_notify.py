#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.ccc.version import Edition
from cmk.cli.internal import CommandContext as CLICommandContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.notifications.cli.notify import _notification_exit_code, cli_command_notify


def test_spool_file_of_commercial_site_fails_without_automation_helper(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, test_edition: Edition
) -> None:
    if test_edition is Edition.COMMUNITY:
        pytest.skip("Spooling via the automation helper is a commercial feature")

    assert (
        cli_command_notify.handler_function(
            CLICommandContext(
                omd_root=tmp_path,
                global_options=CLIGlobalOptions(),
                logger=logging.getLogger(__name__),
            ),
            {},
            ["spoolfile", "/no/such/spoolfile"],
        )
        == CLIExitCode.FAILURE
    )
    assert "automation-helper service is required" in caplog.text


@pytest.mark.parametrize(
    ["returncode", "expected"],
    [
        pytest.param(None, CLIExitCode.SUCCESS, id="no result"),
        pytest.param(0, CLIExitCode.SUCCESS, id="success"),
        pytest.param(1, CLIExitCode.FAILURE, id="temporary failure"),
        pytest.param(2, CLIExitCode.ERROR, id="permanent failure"),
        pytest.param(127, CLIExitCode.ERROR, id="missing interpreter"),
        pytest.param(-9, CLIExitCode.ERROR, id="killed script"),
    ],
)
def test_a_notification_script_result_keeps_its_retry_meaning(
    returncode: int | None, expected: CLIExitCode
) -> None:
    assert _notification_exit_code(returncode) == expected
