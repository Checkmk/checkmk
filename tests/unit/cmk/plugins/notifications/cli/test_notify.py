#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.version import Edition
from cmk.cli.internal import ExitCode, GlobalOptions
from cmk.plugins.notifications.cli.notify import _notification_exit_code, cli_command_notify


def test_spool_file_of_commercial_site_fails_without_automation_helper(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, test_edition: Edition
) -> None:
    if test_edition is Edition.COMMUNITY:
        pytest.skip("Spooling via the automation helper is a commercial feature")

    assert (
        cli_command_notify.handler_function(
            tmp_path, GlobalOptions(), {}, ["spoolfile", "/no/such/spoolfile"]
        )
        == ExitCode.FAILURE
    )
    assert "automation-helper service is required" in caplog.text


@pytest.mark.parametrize(
    ["returncode", "expected"],
    [
        pytest.param(None, ExitCode.SUCCESS, id="no result"),
        pytest.param(0, ExitCode.SUCCESS, id="success"),
        pytest.param(1, ExitCode.FAILURE, id="temporary failure"),
        pytest.param(2, ExitCode.ERROR, id="permanent failure"),
        pytest.param(127, ExitCode.ERROR, id="missing interpreter"),
        pytest.param(-9, ExitCode.ERROR, id="killed script"),
    ],
)
def test_a_notification_script_result_keeps_its_retry_meaning(
    returncode: int | None, expected: ExitCode
) -> None:
    assert _notification_exit_code(returncode) == expected
