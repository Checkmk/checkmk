#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.notifications.cli.notify import (
    _KEEPALIVE_FLAG,
    _LOG_TO_STDOUT_FLAG,
    _notify_request,
    NotifyRequest,
)


def test_the_notify_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        _KEEPALIVE_FLAG: [""],
        _LOG_TO_STDOUT_FLAG: [""],
        CLIArguments(placeholder="MODE", parse=str): ["spoolfile", "/spool/1"],
    }

    assert _notify_request(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == NotifyRequest(log_to_stdout=True, keepalive=True, arguments=("spoolfile", "/spool/1"))
