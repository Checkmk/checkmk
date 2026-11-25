#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk import trace
from cmk.automations.engine import AutomationError, Automations, discover_automations
from cmk.automations.internal import AutomationID, AutomationResult
from cmk.ccc.exceptions import MKGeneralException, MKTimeout
from cmk.ccc.store import lock_checkmk_configuration
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Handler as CLIHandler
from cmk.config import ConfigFileLoadError, load_raw_config
from cmk.plugins.checkmk.cli.automation import (
    AutomationRequest,
    cli_command_automation,
)
from cmk.plugins.checkmk.cli.output import write_stdout

_logger = logging.getLogger(__name__)


_tracer = trace.get_tracer()


def _automation_error_exit_code(error: AutomationError) -> CLIExitCode:
    match error:
        case AutomationError.KNOWN_ERROR:
            return CLIExitCode.FAILURE
        case AutomationError.UNKNOWN_ERROR:
            return CLIExitCode.ERROR


class _ExecuteAutomation(Protocol):
    def __call__(
        self, name: AutomationID, args: list[str], *, omd_root: Path, debug: bool
    ) -> AutomationResult | AutomationError: ...


def _execute_automation(
    name: AutomationID, args: list[str], *, omd_root: Path, debug: bool
) -> AutomationResult | AutomationError:
    automations = Automations(discover_automations(), debug=debug)
    with _tracer.span(
        f"mode_automation[{name}]",
        attributes={
            "cmk.automation.name": name,
            "cmk.automation.args": args,
        },
    ):
        try:
            with (
                lock_checkmk_configuration(cmk.utils.paths.configuration_lockfile)
                if automations.wants_configuration_lock(name)
                else nullcontext(),
            ):
                raw_config = load_raw_config(omd_root=cmk.utils.paths.omd_root)
            automations.update(omd_root, raw_config)
        except (ConfigFileLoadError, MKGeneralException, MKTimeout) as e:
            _logger.error("Loading the configuration failed: %(error)s", {"error": e})  # noqa: TRY400
            if debug:
                raise
            return AutomationError.KNOWN_ERROR
        except Exception:
            _logger.exception("Loading the configuration failed")
            if debug:
                raise
            return AutomationError.UNKNOWN_ERROR

        return automations.execute(name, args)


@dataclass(frozen=True, kw_only=True)
class _AutomationCommand:
    execute: _ExecuteAutomation

    def run(self, context: CLIContext, request: AutomationRequest) -> CLIExitCode:
        if not request.arguments:
            context.logger.error("You need to provide arguments")
            return CLIExitCode.UNKNOWN

        try:
            name, *args = request.arguments
            result = self.execute(
                AutomationID(name),
                args,
                omd_root=context.omd_root,
                debug=context.global_options.debug,
            )
            if isinstance(result, AutomationError):
                return _automation_error_exit_code(result)

            for_cmk_version = (
                cmk_version.__version__
                if request.for_cmk_version is None
                else request.for_cmk_version
            )
            write_stdout(result.serialize(for_cmk_version) + "\n")
            return CLIExitCode.SUCCESS
        except MKGeneralException as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN


cli_handler_automation = CLIHandler(
    command=cli_command_automation, run=_AutomationCommand(execute=_execute_automation).run
)
