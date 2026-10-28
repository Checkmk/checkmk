#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import logging
import signal
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from logging.handlers import WatchedFileHandler
from pathlib import Path
from types import FrameType
from typing import Final

from cmk.ccc.log import CMKFormatter
from cmk.cli.engine.call import call, CommandTracer
from cmk.cli.engine.commands import (
    Command,
    Commands,
    discover_commands,
    general_options,
    Option,
    parse_general_options,
    parse_sub_options,
    write_paged,
    write_stdout,
)
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode

from .arguments import InvalidArguments, parse, ShowHelp

_VERBOSE: Final = 15


def log_level(verbosity: int) -> int:
    match verbosity:
        case 0:
            return logging.INFO
        case 1:
            return _VERBOSE
        case _:
            return logging.DEBUG


def enable_file_logging(path: str, logger: logging.Logger) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    handler = WatchedFileHandler(file_path)
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


_LOG_FILE_OPTION: Final = Option(
    long_option="log-file",
    short_help="Log to the given file (with timestamps) instead of stderr",
    argument=True,
    argument_descr="PATH",
)


@dataclass(frozen=True, kw_only=True)
class Runtime:
    """What the command line reaches for besides its arguments, injectable one by one"""

    discover: Callable[[], Sequence[Command]] = discover_commands
    trace_command: CommandTracer
    on_sigint: Callable[[int, FrameType | None], object] = signal.default_int_handler
    crash_reporter_for: Callable[[Path, Sequence[str], Mapping[str, str]], CrashReporter]
    enable_profiling: Callable[[], None]
    write_profile: Callable[[Path], None]
    page: Callable[[str], None] = write_paged
    write: Callable[[str], None] = write_stdout
    logger: logging.Logger = field(default_factory=configure_logging)


def dispatch(
    command: Callable[[], CLIExitCode],
    logger: logging.Logger,
    crash_reporter: CrashReporter,
    debug: bool,
) -> CLIExitCode:
    """Run the command, mapping what it raises to the exit status it earns"""
    try:
        return command()

    except KeyboardInterrupt:
        logger.error("<Interrupted>")  # noqa: TRY400
        return CLIExitCode.INTERRUPTED

    except OSError as e:
        if e.errno == errno.EPIPE:
            return CLIExitCode.BROKEN_PIPE
        if debug:
            raise
        logger.error(crash_reporter())  # noqa: TRY400
        return CLIExitCode.FAILURE

    except Exception:
        if debug:
            raise
        logger.error(crash_reporter())  # noqa: TRY400
        return CLIExitCode.FAILURE


def run(
    omd_root: Path,
    argv: Sequence[str],
    environ: Mapping[str, str],
    runtime: Runtime,
) -> int:
    signal.signal(signal.SIGINT, runtime.on_sigint)

    commands = Commands(
        plugins=runtime.discover(),
        general_options=[*general_options(), _LOG_FILE_OPTION],
    )

    parsed = parse(commands, argv)
    if isinstance(parsed, InvalidArguments):
        runtime.write(parsed.message)
        return CLIExitCode.UNKNOWN.value

    for option, argument in parsed.options:
        if option.lstrip("-") == _LOG_FILE_OPTION.long_option:
            enable_file_logging(argument, runtime.logger)
    global_options = parse_general_options(parsed.options)
    if global_options.verbosity:
        runtime.logger.setLevel(log_level(global_options.verbosity))
    if global_options.profile:
        runtime.enable_profiling()
        runtime.logger.debug("Enabled profiling")

    logger = runtime.logger.getChild("base")

    def command() -> CLIExitCode:
        if isinstance(parsed, ShowHelp):
            runtime.page(commands.help())
            return CLIExitCode.SUCCESS
        try:
            sub_options = parse_sub_options(parsed.command.sub_options, parsed.options, logger)
        except ValueError as e:
            logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if global_options.debug:
                raise
            return CLIExitCode.UNKNOWN
        return call(
            CLIContext(omd_root=omd_root, global_options=global_options, logger=logger),
            parsed.command,
            parsed.argument,
            sub_options,
            parsed.arguments,
            runtime.trace_command,
        )

    try:
        return dispatch(
            command,
            logger,
            runtime.crash_reporter_for(omd_root, argv, environ),
            global_options.debug,
        ).value
    finally:
        runtime.write_profile(omd_root / "var/check_mk/web")
