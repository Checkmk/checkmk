#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import enum
import os
import signal
import sys
from contextlib import redirect_stdout, suppress
from types import FrameType
from typing import NoReturn

import cmk.ccc.debug
from cmk.ccc import version as cmk_version
from cmk.ccc.exceptions import MKException, MKTimeout

from cmk.utils import log, paths
from cmk.utils.log import console
from cmk.utils.plugin_loader import import_plugins

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


class Automations:
    def __init__(self) -> None:
        super().__init__()
        self._automations: dict[str, Automation] = {}

    def register(self, automation: "Automation") -> None:
        if automation.cmd is None:
            raise TypeError()
        self._automations[automation.cmd] = automation

    def execute(self, cmd: str, args: list[str]) -> AutomationExitCode:
        self._handle_generic_arguments(args)

        try:
            try:
                automation = self._automations[cmd]
            except KeyError:
                raise MKAutomationError(
                    f"Unknown automation command: {cmd!r}"
                    f" (available: {', '.join(sorted(self._automations))})"
                )

            if automation.needs_checks:
                with (
                    tracer.start_as_current_span("load_all_plugins"),
                    redirect_stdout(open(os.devnull, "w")),
                ):
                    log.setup_console_logging()
                    config.load_all_plugins(
                        local_checks_dir=paths.local_checks_dir,
                        checks_dir=paths.checks_dir,
                    )

            if automation.needs_config:
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
            print(
                result.serialize(cmk_version.Version.from_str(cmk_version.__version__)),
                flush=True,
                file=sys.stdout,
            )

        return AutomationExitCode.SUCCESS

    def _handle_generic_arguments(self, args: list[str]) -> None:
        """Handle generic arguments (currently only the optional timeout argument)"""
        if len(args) > 1 and args[0] == "--timeout":
            args.pop(0)
            timeout = int(args.pop(0))

            if timeout:
                signal.signal(signal.SIGALRM, self._raise_automation_timeout)
                signal.alarm(timeout)

    def _raise_automation_timeout(self, signum: int, stackframe: FrameType | None) -> NoReturn:
        raise MKTimeout("Action timed out.")


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
