#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.version import Edition
from cmk.cli.internal import GlobalOptions
from cmk.plugins.notifications.cli.notify import cli_command_notify


def test_spool_file_of_commercial_site_fails_without_automation_helper(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, test_edition: Edition
) -> None:
    if test_edition is Edition.COMMUNITY:
        pytest.skip("Spooling via the automation helper is a commercial feature")

    assert (
        cli_command_notify.handler_function(
            tmp_path, GlobalOptions(), {}, ["spoolfile", "/no/such/spoolfile"]
        )
        == 1
    )
    assert "automation-helper service is required" in caplog.text
