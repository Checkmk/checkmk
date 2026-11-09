#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import signal
import sys
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path

import cmk.ccc.version_info as cmk_version_info
from cmk import trace
from cmk.ccc.site import get_omd_config, omd_site
from cmk.cli.internal import Context as CLIContext
from cmk.crash import (
    BaseCrashReport,
    BaseDetails,
    CrashReportStore,
    make_crash_report_base_path,
)
from cmk.profiling import backend as profiling
from cmk.trace.export import exporter_from_config, init_span_processor

from .arguments import RunCommand
from .discovery import discover_commands
from .output import write_paged, write_stdout
from .run import (
    CommandTracer,
    configure_logging,
    CrashReporter,
    enable_file_logging,
    run,
    Runtime,
)

tracer = trace.get_tracer()


def saving_crash_reporter(
    omd_root: Path, argv: Sequence[str], environ: Mapping[str, str]
) -> CrashReporter:
    def report() -> str:
        crash = BaseCrashReport(
            crash_report_base_path=make_crash_report_base_path(omd_root),
            crash_info=BaseCrashReport.make_crash_info(
                cmk_version_info.get_general_version_infos(omd_root),
                BaseDetails(argv=list(argv), env=dict(environ)),
            ),
        )
        CrashReportStore().save(crash)
        return (
            f"{crash.crash_info['exc_type']}: {crash.crash_info['exc_value']} "
            f"- please submit a crash report! (Crash-ID: {crash.ident_to_text()})"
        )

    return report


def tracing(environ: Mapping[str, str]) -> CommandTracer:
    @contextmanager
    def traced(context: CLIContext, run_command: RunCommand) -> Iterator[None]:
        omd_config = get_omd_config(context.omd_root)
        if (send_config := trace.trace_send_config(omd_config)).enabled:
            init_span_processor(
                trace.init_tracing(
                    service_namespace=trace.service_namespace_from_config("", omd_config),
                    service_name="cmk",
                    service_instance_id=omd_site(),
                    extra_resource_attributes=trace.resource_attributes_from_config(
                        context.omd_root
                    ),
                ),
                exporter_from_config(exporter_log_level=logging.CRITICAL, config=send_config),
            )
        with tracer.span(
            f"command[{run_command.command.name}]",
            attributes={
                "cmk.cli.command.name": run_command.command.name,
                "cmk.cli.command.args": repr(
                    (context.global_options, run_command.options, run_command.args)
                ),
            },
            context=trace.extract_context_from_environment(dict(environ)),
        ):
            yield

    return traced


def _write_profile(omd_root: Path) -> None:
    profiling.output_profile(profiling.profiles_dir(omd_root))


def main() -> int:
    match os.environ.get("OMD_ROOT"):
        case None:
            sys.stderr.write("Checkmk can be used only as site user.\n")
            return 1
        case omd_root:
            return run(
                Path(omd_root),
                sys.argv,
                os.environ,
                Runtime(
                    discover=discover_commands,
                    trace_command=tracing(os.environ),
                    on_sigint=signal.default_int_handler,
                    crash_reporter_for=saving_crash_reporter,
                    enable_profiling=profiling.enable,
                    log_to_file=enable_file_logging,
                    write_profile=_write_profile,
                    page=write_paged,
                    write=write_stdout,
                    logger=configure_logging(),
                ),
            )
