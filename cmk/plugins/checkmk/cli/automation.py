#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --automation" command, the entry point of the automation calls."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import cmk.ccc.version as cmk_version
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue


def _parse_version(argument: str) -> str:
    cmk_version.Version.from_str(argument)
    return argument


_FOR_CMK_VERSION_VALUE: Final = CLIValue(
    long="for-cmk-version",
    placeholder="VERSION",
    help=(
        "Serialize the result for a site running this Checkmk version"
        " (default: the version of this site)"
    ),
    parse=_parse_version,
)


@dataclass(frozen=True, kw_only=True)
class AutomationRequest:
    for_cmk_version: str | None
    arguments: Sequence[str]


def _automation_request(options: CLIReader) -> AutomationRequest:
    return AutomationRequest(
        for_cmk_version=options.value(_FOR_CMK_VERSION_VALUE),
        arguments=options.arguments(CLIArguments(placeholder="COMMAND...", parse=str)),
    )


cli_command_automation = CLICommand(
    name="automation",
    handler="cmk.plugins.checkmk.cli.handlers.automation:cli_handler_automation",
    long="automation",
    request=_automation_request,
    help="Internal helper to invoke Check_MK actions",
)
