#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LocalAutomationResult:
    exit_code: int
    output: str
    command_description: str
    error: str | None = None


class AutomationExecutor(Protocol):
    def execute(
        self,
        command: str,
        args: Sequence[str],
        stdin: str,
        logger: logging.Logger,
        timeout: int | None,
    ) -> LocalAutomationResult: ...

    def command_description(
        self,
        command: str,
        args: Sequence[str],
        logger: logging.Logger,
        timeout: int | None,
    ) -> str: ...


def arguments_with_timeout(args: Sequence[str], timeout: int | None) -> Sequence[str]:
    return args if timeout is None else ["--timeout", str(timeout), *args]
