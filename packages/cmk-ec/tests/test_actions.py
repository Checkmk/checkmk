#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Running the commands of the actions of the EC"""

import logging

import pytest

from cmk.ec.actions import run_in_subprocess


def _run_script(script: str) -> None:
    run_in_subprocess(
        args=["/bin/sh"],
        input_=script,
        env=None,
        description="executing script",
        logger=logging.getLogger("cmk.mkeventd"),
    )


def test_successful_command_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    _run_script("true")

    assert caplog.messages == ["executing script succeeded"]


def test_failed_command_is_logged_with_its_exit_code_and_output(
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run_script("echo disk full; echo no space left >&2; exit 3")

    assert caplog.messages == [
        "executing script failed with exit code 3",
        "  output: disk full",
        "  output: no space left",
    ]
