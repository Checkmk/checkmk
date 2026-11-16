#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --notify" command."""

from dataclasses import dataclass
from typing import Final

from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Reader as CLIReader

_LOG_TO_STDOUT_FLAG: Final = CLIFlag(
    long="log-to-stdout",
    help="Also write log messages to console",
)

_KEEPALIVE_FLAG: Final = CLIFlag(
    long="keepalive",
    help="Execute in keepalive mode (Commercial editions only)",
)


@dataclass(frozen=True, kw_only=True)
class NotifyRequest:
    log_to_stdout: bool
    keepalive: bool


def _notify_request(options: CLIReader) -> NotifyRequest:
    return NotifyRequest(
        log_to_stdout=options.flag(_LOG_TO_STDOUT_FLAG),
        keepalive=options.flag(_KEEPALIVE_FLAG),
    )


cli_command_notify = CLICommand(
    name="notify",
    handler="cmk.plugins.notifications.cli.handlers.notify:cli_handler_notify",
    long="notify",
    request=_notify_request,
    arguments=CLIArguments(placeholder="MODE", parse=str),
    help="Used to send notifications from core",
)
