#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.cli.internal import CommandContext, ExitCode, GlobalOptions
from cmk.plugins.checkmk.cli.localize import cli_command_localize


def _context() -> CommandContext:
    return CommandContext(
        omd_root=Path("/nonexistent"),
        global_options=GlobalOptions(),
        logger=logging.getLogger(__name__),
    )


@pytest.mark.parametrize(
    "args", [[], ["frobnicate", "de"]], ids=["without a command", "with an unknown command"]
)
def test_a_wrong_invocation_fails(args: list[str]) -> None:
    assert cli_command_localize.handler_function(_context(), {}, args) == ExitCode.FAILURE
