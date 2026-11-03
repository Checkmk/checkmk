#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.checkengine.specs.checkresults import ServiceState
from cmk.cli.internal import ExitCode as CLIExitCode


def state_exit_code(state: ServiceState) -> CLIExitCode:
    match state:
        case 0:
            return CLIExitCode.SUCCESS
        case 1:
            return CLIExitCode.FAILURE
        case 2:
            return CLIExitCode.ERROR
        case _:
            return CLIExitCode.UNKNOWN
