#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import enum
import os
import signal
import sys
from contextlib import nullcontext, redirect_stdout, suppress
from types import FrameType
from typing import NoReturn

import cmk.ccc.debug
from cmk.ccc import version as cmk_version
from cmk.ccc.exceptions import MKException, MKTimeout

from cmk.utils import log, paths
from cmk.utils.log import console
from cmk.utils.plugin_loader import import_plugins
from cmk.utils.timeout import Timeout

from cmk.automations.results import ABCAutomationResult

from cmk.base import config, profiling

from cmk import trace

tracer = trace.get_tracer()


# TODO: Inherit from MKGeneralException
class MKAutomationError(MKException):
    pass


class AutomationExitCode(enum.IntEnum):
    """Supported exit code for an executed automation command."""

    SUCCESS = 0
    KNOWN_ERROR = 1
    UNKNOWN_ERROR = 2
    SYSTEM_EXIT = 3


class Automations:
    def __init__(self) -> None:
        super().__init__()
        self._automations: dict[str, Automation] = {}

    def register(self, automation: "Automation") -> None:
        if automation.cmd is None:
            raise TypeError()
        self._automations[automation.cmd] = automation

    # TODO: remove `reload_config` when automation helper is fully integrated.
    def execute(
        self, cmd: str, args: list[str], *, reload_config: bool = True
    ) -> AutomationExitCode:
        remaining_args, timeout = self._extract_timeout_from_args(args)
        with nullcontext() if timeout is None else Timeout(timeout, message="Action timed out."):
            return self._execute(cmd, remaining_args, reload_config=reload_config)

    def _execute(
        self, cmd: str, args: list[str], *, reload_config: bool = True
    ) -> AutomationExitCode:
        try:
            try:
                automation = self._automations[cmd]
            except KeyError:
                raise MKAutomationError(
                    f"Unknown automation command: {cmd!r}"
                    f" (available: {', '.join(sorted(self._automations))})"
                )

            if reload_config and automation.needs_checks:
                with (
                    tracer.start_as_current_span("load_all_plugins"),
                    redirect_stdout(open(os.devnull, "w")),
                ):
                    log.setup_console_logging()
                    config.load_all_plugins(
                        local_checks_dir=paths.local_checks_dir,
                        checks_dir=paths.checks_dir,
                    )

            if reload_config and automation.needs_config:
                with tracer.start_as_current_span("load_config"):
                    config.load(validate_hosts=False)

            with tracer.start_as_current_span(f"execute_automation[{cmd}]"):
                result = automation.execute(args)

        except (MKAutomationError, MKTimeout) as e:
            console.error(f"{e}", file=sys.stderr)
            if cmk.ccc.debug.enabled():
                raise
            return AutomationExitCode.KNOWN_ERROR

        except Exception as e:
            if cmk.ccc.debug.enabled():
                raise
            console.error(f"{e}", file=sys.stderr)
            return AutomationExitCode.UNKNOWN_ERROR

        finally:
            profiling.output_profile()

        with suppress(IOError):
            sys.stdout.write(
                result.serialize(cmk_version.Version.from_str(cmk_version.__version__)) + "\n"
            )
            sys.stdout.flush()

        return AutomationExitCode.SUCCESS

    def _extract_timeout_from_args(self, args: list[str]) -> tuple[list[str], int | None]:
        match args:
            case ["--timeout", timeout, *remaining_args]:
                return remaining_args, int(timeout)
            case _:
                return args, None


class Automation(abc.ABC):
    cmd: str | None = None
    needs_checks = False
    needs_config = False

    @abc.abstractmethod
    def execute(self, args: list[str]) -> ABCAutomationResult: ...


#
# Initialize the modes object and load all available modes
#

automations = Automations()

import_plugins(__file__, __package__)
