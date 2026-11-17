#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Sequence

from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Handler as CLIHandler
from cmk.plugins.checkmk.cli.package import (
    cli_command_package,
    DEPRECATION_MSG,
)


def _run_package(_context: CLIContext, arguments: Sequence[str], _args: CLIArgs) -> CLIExitCode:
    sys.stderr.write(DEPRECATION_MSG % " ".join(("", *arguments)) + "\n")
    return CLIExitCode.FAILURE


cli_handler_package = CLIHandler(command=cli_command_package, run=_run_package)
