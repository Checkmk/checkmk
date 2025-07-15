#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Execute cmk automation commands via subprocess"""

import logging
import os
import subprocess
from collections.abc import Sequence

from cmk import trace
from cmk.utils.log import VERBOSE

from .automation_executor import arguments_with_timeout, AutomationExecutor, LocalAutomationResult


class SubprocessExecutor(AutomationExecutor):
    def execute(
        self,
        command: str,
        args: Sequence[str],
        stdin: str,
        logger: logging.Logger,
        timeout: int | None,
    ) -> LocalAutomationResult:
        cmd = _automation_command(command, args, logger, timeout)
        cmd_descr = self.command_description(command, args, logger, timeout)

        logger.info("RUN: %s" % cmd_descr)
        span = trace.get_current_span()
        span.set_attribute("cmk.automation.command", cmd_descr)
        logger.info("STDIN: %r" % stdin)

        completed_process = subprocess.run(
            cmd,
            capture_output=True,
            close_fds=True,
            encoding="utf-8",
            input=stdin,
            check=False,
            # Set the environment for the trace context (TRACEPARENT + optional TRACESTATE)
            env=dict(os.environ) | trace.context_for_environment(),
        )

        if completed_process.stderr:
            logger.warning(f"'{cmd_descr}' returned stderr: '{completed_process.stderr}'")

        return LocalAutomationResult(
            exit_code=completed_process.returncode,
            output=completed_process.stdout,
            command_description=cmd_descr,
            error=completed_process.stderr,
        )

    def command_description(
        self, command: str, args: Sequence[str], logger: logging.Logger, timeout: int | None
    ) -> str:
        return subprocess.list2cmdline(_automation_command(command, args, logger, timeout))


def _automation_command(
    command: str, args: Sequence[str], logger: logging.Logger, timeout: int | None
) -> list[str]:
    cmd = ["check_mk"]
    if (log_level := logger.getEffectiveLevel()) <= logging.DEBUG:
        cmd.append("-vv")
    elif log_level <= VERBOSE:
        cmd.append("-v")

    return [*cmd, "--automation", command, *arguments_with_timeout(args, timeout)]
