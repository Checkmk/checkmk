#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import signal
import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from logging.handlers import WatchedFileHandler
from pathlib import Path
from types import FrameType
from typing import Final

from cmk.ccc.log import CMKFormatter
from cmk.cli.engine.commands import Commands, DiscoveredCommand
from cmk.cli.engine.discovery import discover_commands
from cmk.cli.engine.output import write_paged, write_stdout
from cmk.cli.engine.readers import ParsedOptions
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions

from .arguments import InvalidArguments, parse, rejection, RunCommand, ShowHelp

type CommandTracer = Callable[[CLIContext, RunCommand], AbstractContextManager[None]]

_VERBOSE: Final = 15


def log_level(verbosity: int) -> int:
    match verbosity:
        case 0:
            return logging.INFO
        case 1:
            return _VERBOSE
        case _:
            return logging.DEBUG


def enable_file_logging(path: Path, logger: logging.Logger) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = WatchedFileHandler(path)
    handler.setFormatter(CMKFormatter())
    del logger.handlers[:]
    logger.addHandler(handler)


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("cmk")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        # astrein: disable=logging-formatter
        logging.Formatter("[%(levelname)s] %(message)s")
    )
    logger.addHandler(handler)
    return logger


type CrashReporter = Callable[[], str]
"""Saves a crash report and returns the message to print instead of a traceback"""


@dataclass(frozen=True, kw_only=True)
class Runtime:
    discover: Callable[[], Sequence[DiscoveredCommand]] = discover_commands
    trace_command: CommandTracer
    on_sigint: Callable[[int, FrameType | None], object] = signal.default_int_handler
    crash_reporter_for: Callable[[Path, Sequence[str], Mapping[str, str]], CrashReporter]
    enable_profiling: Callable[[], None]
    log_to_file: Callable[[Path, logging.Logger], None]
    write_profile: Callable[[Path], None]
    page: Callable[[str], None] = write_paged
    write: Callable[[str], None] = write_stdout
    logger: logging.Logger = field(default_factory=configure_logging)


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


def _apply_global_options(global_options: CLIGlobalOptions, runtime: Runtime) -> None:
    if global_options.log_file is not None:
        runtime.log_to_file(global_options.log_file, runtime.logger)
    if global_options.verbosity:
        runtime.logger.setLevel(log_level(global_options.verbosity))
    if global_options.profile:
        runtime.enable_profiling()
        runtime.logger.debug("Enabled profiling")


def run(
    omd_root: Path,
    argv: Sequence[str],
    environ: Mapping[str, str],
    runtime: Runtime,
) -> int:
    signal.signal(signal.SIGINT, runtime.on_sigint)

    commands = Commands(plugins=runtime.discover())
    logger = runtime.logger.getChild("base")

    parsed = parse(commands, argv, logger)
    if isinstance(parsed, InvalidArguments):
        runtime.write(parsed.message)
        return CLIExitCode.UNKNOWN.value

    request = parsed
    _apply_global_options(request.global_options, runtime)

    def command() -> CLIExitCode:
        if isinstance(request, ShowHelp):
            runtime.page(commands.help())
            return CLIExitCode.SUCCESS
        try:
            bound = request.command.bind(ParsedOptions(request.options, logger))
        except ValueError as error:
            runtime.write(rejection(argv, error).message)
            return CLIExitCode.UNKNOWN
        context = CLIContext(
            omd_root=omd_root, global_options=request.global_options, logger=logger
        )
        with runtime.trace_command(context, request):
            return bound(context, request.args)

    try:
        return dispatch(
            command,
            logger,
            runtime.crash_reporter_for(omd_root, argv, environ),
            debug=request.global_options.debug,
        ).value
    finally:
        runtime.write_profile(omd_root / "var/check_mk/web")
