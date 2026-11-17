#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.handlers.package import cli_handler_package


def test_the_retired_command_refers_to_mkp_on_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    context = CLIContext(
        omd_root=Path("/omd/sites/mysite"),
        global_options=CLIGlobalOptions(),
        logger=logging.getLogger(__name__),
    )

    cli_handler_package.run(context, ("list",), ())

    assert capsys.readouterr().err == (
        "This command is no longer supported. Please use `mkp list` instead.\n"
    )
