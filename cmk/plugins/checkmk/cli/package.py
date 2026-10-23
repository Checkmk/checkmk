#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The deprecated "cmk --package" command."""

import sys
from pathlib import Path

from cmk.cli.internal import Args, CLICommand, GlobalOptions, Options

_DEPRECATION_MSG = "This command is no longer supported. Please use `mkp%s` instead."


def _fail_with_deprecation_msg(
    _omd_root: Path, _global_options: GlobalOptions, _options: Options, argv: Args
) -> int:
    sys.stdout.write(_DEPRECATION_MSG % " ".join(("", *argv)) + "\n")
    return 1


cli_command_package = CLICommand(
    long_option="package",
    short_option="P",
    handler_function=_fail_with_deprecation_msg,
    argument=True,
    argument_descr="COMMAND",
    argument_optional=True,
    short_help="DEPRECATED: Do package operations",
    long_help=[_DEPRECATION_MSG % ""],
)
