#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --automation" command, the entry point of the automation calls."""

import logging
import sys
from contextlib import nullcontext, suppress
from pathlib import Path

import cmk.ccc.debug
import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk import trace
from cmk.automations.engine import AutomationError
from cmk.ccc.exceptions import MKBailOut, MKGeneralException, MKTimeout
from cmk.cli.engine.commands import option_string
from cmk.cli.internal import (
    Args,
    CLICommand,
    CLIOption,
    CommandContext,
    ExitCode,
    GlobalOptions,
    Options,
)
from cmk.profiling import backend as profiling

logger = logging.getLogger(__name__)
tracer = trace.get_tracer()


def _automation_error_exit_code(error: AutomationError) -> ExitCode:
    match error:
        case AutomationError.KNOWN_ERROR:
            return ExitCode.FAILURE
        case AutomationError.UNKNOWN_ERROR:
            return ExitCode.ERROR


def _mode_automation(
    omd_root: Path, global_options: GlobalOptions, options: Options, args: Args
) -> ExitCode:
    from cmk.automations.engine import Automations, discover_automations
    from cmk.automations.internal import AutomationID
    from cmk.base import config
    from cmk.ccc.store import lock_checkmk_configuration

    if not args:
        raise MKBailOut("You need to provide arguments")

    name, automation_args = AutomationID(args[0]), list(args[1:])
    for_cmk_version = _for_cmk_version(options)
    automations = Automations(discover_automations())
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
                config.exit_on_config_file_load_error(),
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

        try:
            result = automations.execute(name, automation_args)
        finally:
            profiling.output_profile(cmk.utils.paths.profiles_dir)
        if isinstance(result, AutomationError):
            return _automation_error_exit_code(result)
        with suppress(IOError):
            sys.stdout.write(result.serialize(for_cmk_version) + "\n")
            sys.stdout.flush()
        return ExitCode.SUCCESS


def _run_automation(context: CommandContext, options: Options, args: Args) -> ExitCode:
    if context.global_options.debug:
        # exit_on_config_file_load_error() reads cmk.ccc.debug
        cmk.ccc.debug.enable()
    try:
        return _mode_automation(context.omd_root, context.global_options, options, args)
    except (MKBailOut, MKGeneralException) as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return ExitCode.UNKNOWN


def _for_cmk_version(options: Options) -> str:
    """The version to serialize the result for, checked before the automation runs"""
    if (for_cmk_version := option_string(options, "for-cmk-version")) is None:
        return cmk_version.__version__
    try:
        cmk_version.Version.from_str(for_cmk_version)
    except ValueError as e:
        raise MKBailOut(f"--for-cmk-version: {e}") from e
    return for_cmk_version


cli_command_automation = CLICommand(
    long_option="automation",
    handler_function=_run_automation,
    argument=True,
    argument_descr="COMMAND...",
    argument_optional=True,
    short_help="Internal helper to invoke Check_MK actions",
    sub_options=[
        CLIOption(
            long_option="for-cmk-version",
            argument=True,
            argument_descr="VERSION",
            short_help=(
                "Serialize the result for a site running this Checkmk version"
                " (default: the version of this site)"
            ),
        ),
    ],
)
