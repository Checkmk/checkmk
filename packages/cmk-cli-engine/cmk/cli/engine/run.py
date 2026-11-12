#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import signal
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from types import FrameType
from typing import assert_never

from cmk.ccc.log import verbosity_to_log_level
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions

from .arguments import InvalidArguments, parse, rejection, RunCommand, ShowHelp
from .commands import Commands, DiscoveredCommand
from .options import GlobalOptions
from .readers import ParsedOptions

type CommandTracer = Callable[[CLIContext, RunCommand], AbstractContextManager[None]]


type CrashReporter = Callable[[], str]
"""Saves a crash report and returns the message to print instead of a traceback"""


@dataclass(frozen=True, kw_only=True)
class Runtime:
    discover: Callable[[], Sequence[DiscoveredCommand]]
    trace_command: CommandTracer
    on_sigint: Callable[[int, FrameType | None], object]
    crash_reporter_for: Callable[[Path, Sequence[str], Mapping[str, str]], CrashReporter]
    enable_profiling: Callable[[], None]
    log_to_file: Callable[[Path, logging.Logger], None]
    write_profile: Callable[[Path], None]
    page: Callable[[str], None]
    write_error: Callable[[str], None]
    logger: logging.Logger


def dispatch(
    command: Callable[[], CLIExitCode],
    logger: logging.Logger,
    crash_reporter: CrashReporter,
    *,
    debug: bool,
) -> CLIExitCode:
    try:
        return command()

    except KeyboardInterrupt:
        logger.error("<Interrupted>")  # noqa: TRY400
        return CLIExitCode.INTERRUPTED

    except BrokenPipeError:
        return CLIExitCode.BROKEN_PIPE

    except Exception:
        if debug:
            raise
        logger.error(crash_reporter())  # noqa: TRY400
        return CLIExitCode.FAILURE


def _apply_global_options(global_options: GlobalOptions, runtime: Runtime) -> None:
    if global_options.log_file is not None:
        runtime.log_to_file(global_options.log_file, runtime.logger)
    runtime.logger.setLevel(verbosity_to_log_level(global_options.verbosity))
    if global_options.profile:
        runtime.enable_profiling()
        runtime.logger.debug("Enabled profiling")


def _show_help(commands: Commands, runtime: Runtime) -> CLIExitCode:
    runtime.page(commands.help())
    return CLIExitCode.SUCCESS


def _run_command(
    run_command: RunCommand, context: CLIContext, argv: Sequence[str], runtime: Runtime
) -> CLIExitCode:
    try:
        bound = run_command.command.bind(ParsedOptions(run_command.options, context.logger))
    except ValueError as error:
        runtime.write_error(rejection(argv, error))
        return CLIExitCode.UNKNOWN
    with runtime.trace_command(context, run_command):
        return bound(context, run_command.args)


def run(
    omd_root: Path,
    argv: Sequence[str],
    environ: Mapping[str, str],
    runtime: Runtime,
) -> int:
    signal.signal(signal.SIGINT, runtime.on_sigint)

    commands = Commands(commands=runtime.discover())
    logger = runtime.logger.getChild("cli")

    match parse(commands, argv, logger):
        case InvalidArguments(message=message):
            runtime.write_error(message)
            return CLIExitCode.UNKNOWN.value
        case ShowHelp(global_options=global_options):
            command = partial(_show_help, commands, runtime)
        case RunCommand(global_options=global_options) as run_command:
            context = CLIContext(
                omd_root=omd_root,
                global_options=CLIGlobalOptions(debug=global_options.debug),
                logger=logger,
            )
            command = partial(_run_command, run_command, context, argv, runtime)
        case unexpected:
            assert_never(unexpected)

    _apply_global_options(global_options, runtime)
    try:
        return dispatch(
            command,
            logger,
            runtime.crash_reporter_for(omd_root, argv, environ),
            debug=global_options.debug,
        ).value
    finally:
        runtime.write_profile(omd_root)
