#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.check import _checking_request
from cmk.plugins.checkmk.cli.handlers.check import cli_handler_check


def test_more_than_a_host_and_an_address_are_rejected() -> None:
    logger = logging.getLogger(__name__)
    context = CLIContext(
        omd_root=Path("/nonexistent"), global_options=CLIGlobalOptions(), logger=logger
    )
    given: Mapping[CLIDeclaration, Sequence[str]] = {}

    request = _checking_request(CLIReader(lambda declaration: given.get(declaration, ())))

    assert (
        cli_handler_check.run(context, request, ["host1", "host2", "host3"]) == CLIExitCode.UNKNOWN
    )
