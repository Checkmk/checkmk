#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import logging
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from logging.handlers import WatchedFileHandler
from pathlib import Path
from typing import Final, override, Self

import cmk.ccc.debug
import cmk.ccc.version_info as cmk_version_info
from cmk import trace
from cmk.ccc.exceptions import (
    MKBailOut,
    MKGeneralException,
    MKTerminate,
    raise_mkterminate_on_sigint,
)
from cmk.ccc.log import CMKFormatter
from cmk.ccc.site import get_omd_config, omd_site
from cmk.cli.engine.call import call
from cmk.cli.engine.commands import (
    Command,
    Commands,
    discover_commands,
    general_options,
    Option,
    parse_general_options,
    write_paged,
    write_stdout,
)
from cmk.crash import (
    ABCCrashReport,
    BaseDetails,
    CrashReportStore,
    make_crash_report_base_path,
    VersionInfo,
)
from cmk.profiling import backend as profiling
from cmk.trace.export import (
    exporter_from_config,
    init_span_processor,
)

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


def start_tracing(omd_root: Path) -> None:
    init_span_processor(
        trace.init_tracing(
            service_namespace=trace.service_namespace_from_config(
                "", omd_config := get_omd_config(omd_root)
            ),
            service_name="cmk",
            service_instance_id=omd_site(),
            extra_resource_attributes=trace.resource_attributes_from_config(omd_root),
        ),
        exporter_from_config(
            exporter_log_level=logging.CRITICAL,
            config=trace.trace_send_config(omd_config),
        ),
    )


class CrashReport(ABCCrashReport[BaseDetails]):
    @classmethod
    @override
    def type(cls) -> str:
        return "base"

    @classmethod
    def from_exception(
        cls,
        *,
        crash_report_base_path: Path,
        version_info: VersionInfo,
        argv: Sequence[str],
        environ: Mapping[str, str],
    ) -> Self:
        return cls(
            crash_report_base_path=crash_report_base_path,
            crash_info=cls.make_crash_info(
                version_info,
                BaseDetails(
                    argv=list(argv),
                    env=dict(environ),
                ),
            ),
        )

    def save(self) -> None:
        CrashReportStore().save(self)

    def render(self) -> str:
        return (
            f"{self.crash_info['exc_type']}: {self.crash_info['exc_value']} "
            f"- please submit a crash report! (Crash-ID: {self.ident_to_text()})"
        )


type CrashReporter = Callable[[], str]
"""Saves a crash report and returns the message to print instead of a traceback"""


def saving_crash_reporter(
    omd_root: Path, argv: Sequence[str], environ: Mapping[str, str]
) -> CrashReporter:
    def report() -> str:
        crash = CrashReport.from_exception(
            crash_report_base_path=make_crash_report_base_path(omd_root),
            version_info=cmk_version_info.get_general_version_infos(omd_root),
            argv=argv,
            environ=environ,
        )
        crash.save()
        return crash.render()

    return report


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
    start_tracing: Callable[[Path], None] = start_tracing
    on_sigint: Callable[[], None] = raise_mkterminate_on_sigint
    crash_reporter_for: Callable[[Path, Sequence[str], Mapping[str, str]], CrashReporter] = (
        saving_crash_reporter
    )
    enable_debug: Callable[[], None] = cmk.ccc.debug.enable
    debug_enabled: Callable[[], bool] = cmk.ccc.debug.enabled
    enable_profiling: Callable[[], None] = profiling.enable
    write_profile: Callable[[Path], None] = profiling.output_profile
    page: Callable[[str], None] = write_paged
    write: Callable[[str], None] = write_stdout
    logger: logging.Logger = field(default_factory=configure_logging)


def dispatch(
    command: Callable[[], int],
    logger: logging.Logger,
    crash_reporter: CrashReporter,
    debug_enabled: Callable[[], bool] = cmk.ccc.debug.enabled,
) -> int:
    """Run the command, mapping what it raises to the exit status it earns"""
    try:
        return command()

    except MKTerminate:
        logger.error("<Interrupted>")  # noqa: TRY400
        return 1

    except (MKGeneralException, MKBailOut) as e:
        logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if debug_enabled():
            raise
        return 3

    except OSError as e:
        if e.errno == errno.EPIPE:
            return 4
        logger.error(crash_reporter())  # noqa: TRY400
        if debug_enabled():
            raise
        return 1

    except Exception:
        logger.error(crash_reporter())  # noqa: TRY400
        if debug_enabled():
            raise
        return 1


def run(
    omd_root: Path,
    argv: Sequence[str],
    environ: Mapping[str, str],
    runtime: Runtime,
) -> int:
    runtime.on_sigint()
    runtime.start_tracing(omd_root)

    commands = Commands(
        plugins=runtime.discover(),
        general_options=[*general_options(), _LOG_FILE_OPTION],
        page=runtime.page,
    )

    parsed = parse(commands, argv)
    if isinstance(parsed, InvalidArguments):
        runtime.write(parsed.message)
        return 1

    for option, argument in parsed.options:
        if option.lstrip("-") == _LOG_FILE_OPTION.long_option:
            enable_file_logging(argument, runtime.logger)
    global_options = parse_general_options(parsed.options)
    if global_options.verbosity:
        runtime.logger.setLevel(log_level(global_options.verbosity))
    if global_options.debug:
        runtime.enable_debug()
    if global_options.profile:
        runtime.enable_profiling()
        runtime.logger.debug("Enabled profiling")

    def command() -> int:
        if isinstance(parsed, ShowHelp):
            runtime.page(commands.help())
            return 0
        return call(
            omd_root,
            parsed.command,
            global_options,
            parsed.argument,
            parsed.options,
            parsed.arguments,
            trace.extract_context_from_environment(dict(environ)),
        )

    try:
        return dispatch(
            command,
            runtime.logger.getChild("base"),
            runtime.crash_reporter_for(omd_root, argv, environ),
            runtime.debug_enabled,
        )
    finally:
        runtime.write_profile(omd_root / "var/check_mk/web")
