#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import no_options as cli_no_options

cli_command_localize = CLICommand(
    name="localize",
    handler="cmk.plugins.checkmk.cli.handlers.localize:cli_handler_localize",
    long="localize",
    request=cli_no_options,
    arguments=CLIArguments(placeholder="COMMAND", parse=str),
    help="Do localization operations",
    description=[
        (
            "Brings you into localization mode. You can create "
            "and/or improve the localization of Check_MKs GUI. "
            "Call without arguments for a help on localization."
        )
    ],
)
