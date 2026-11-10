#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.localize import _mode_localize


def _context() -> CLIContext:
    return CLIContext(
        omd_root=Path("/nonexistent"),
        global_options=CLIGlobalOptions(),
        logger=logging.getLogger(__name__),
    )


@pytest.mark.parametrize(
    "args", [[], ["frobnicate", "de"]], ids=["without a command", "with an unknown command"]
)
def test_a_wrong_invocation_fails(args: list[str]) -> None:
    assert _mode_localize(_context(), None, args) == CLIExitCode.FAILURE


def test_a_call_without_a_command_shows_the_usage_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mode_localize(_context(), None, [])

    assert "Usage:" in capsys.readouterr().err
