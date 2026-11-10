#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.cli.engine.commands import bind as cli_bind
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.package import cli_command_package


def test_the_retired_command_refers_to_mkp_on_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    logger = logging.getLogger(__name__)
    bound = cli_bind(cli_command_package, CLIParsedOptions([], logger))
    context = CLIContext(
        omd_root=Path("/nonexistent"), global_options=CLIGlobalOptions(), logger=logger
    )

    bound(context, ["list"])

    assert "`mkp list`" in capsys.readouterr().err
