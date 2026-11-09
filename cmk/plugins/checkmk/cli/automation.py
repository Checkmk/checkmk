#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --automation" command, the entry point of the automation calls."""

import logging
import sys
from contextlib import nullcontext, suppress
from pathlib import Path
from typing import Final

import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk import trace
from cmk.automations.engine import AutomationError
from cmk.ccc.exceptions import MKBailOut, MKGeneralException, MKTimeout
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue

logger = logging.getLogger(__name__)
tracer = trace.get_tracer()


def _automation_error_exit_code(error: AutomationError) -> CLIExitCode:
    match error:
        case AutomationError.KNOWN_ERROR:
            return CLIExitCode.FAILURE
        case AutomationError.UNKNOWN_ERROR:
            return CLIExitCode.ERROR


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


def _for_cmk_version_request(options: CLIReader) -> str | None:
    return options.value(_FOR_CMK_VERSION_VALUE)


def _mode_automation(
    omd_root: Path, global_options: CLIGlobalOptions, requested_version: str | None, args: CLIArgs
) -> CLIExitCode:
    from cmk.automations.engine import Automations, discover_automations
    from cmk.automations.internal import AutomationID
    from cmk.base import config
    from cmk.ccc.store import lock_checkmk_configuration

    if not args:
        raise MKBailOut("You need to provide arguments")

    name, automation_args = AutomationID(args[0]), list(args[1:])
    for_cmk_version = cmk_version.__version__ if requested_version is None else requested_version
    automations = Automations(discover_automations(), debug=global_options.debug)
    with tracer.span(
        f"mode_automation[{name}]",
        attributes={
            "cmk.automation.name": name,
            "cmk.automation.args": automation_args,
        },
    ):
        # Report a broken configuration the way the engine reports a failing automation.
        try:
            with (
                lock_checkmk_configuration(cmk.utils.paths.configuration_lockfile)
                if automations.wants_configuration_lock(name)
                else nullcontext(),
                config.exit_on_config_file_load_error(debug=global_options.debug),
            ):
                raw_config = config.load_raw_config()
            automations.update(omd_root, raw_config)
        except (MKGeneralException, MKTimeout) as e:
            logger.error("Loading the configuration failed: %(error)s", {"error": e})  # noqa: TRY400
            if global_options.debug:
                raise
            return _automation_error_exit_code(AutomationError.KNOWN_ERROR)
        except Exception:
            logger.exception("Loading the configuration failed")
            if global_options.debug:
                raise
            return _automation_error_exit_code(AutomationError.UNKNOWN_ERROR)

        result = automations.execute(name, automation_args)
        if isinstance(result, AutomationError):
            return _automation_error_exit_code(result)
        with suppress(IOError):
            sys.stdout.write(result.serialize(for_cmk_version) + "\n")
            sys.stdout.flush()
        return CLIExitCode.SUCCESS


def _run_automation(
    context: CLIContext, requested_version: str | None, args: CLIArgs
) -> CLIExitCode:
    try:
        return _mode_automation(context.omd_root, context.global_options, requested_version, args)
    except (MKBailOut, MKGeneralException) as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


cli_command_automation = CLICommand(
    name="automation",
    long="automation",
    request=_for_cmk_version_request,
    handler=_run_automation,
    arguments=CLIArguments("COMMAND...", optional=True),
    help="Internal helper to invoke Check_MK actions",
)
