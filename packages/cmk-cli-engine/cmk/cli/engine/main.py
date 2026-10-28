#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import sys
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import override, Self

import cmk.ccc.version_info as cmk_version_info
from cmk import trace
from cmk.ccc.site import get_omd_config, omd_site
from cmk.cli.engine.commands import Command
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import CommandContext as CLICommandContext
from cmk.cli.internal import Options
from cmk.crash import (
    ABCCrashReport,
    BaseDetails,
    CrashReportStore,
    make_crash_report_base_path,
    VersionInfo,
)
from cmk.profiling import backend as profiling
from cmk.trace.export import exporter_from_config, init_span_processor

from .call import CommandTracer
from .run import CrashReporter, run, Runtime

tracer = trace.get_tracer()


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


def tracing(environ: Mapping[str, str]) -> CommandTracer:
    @contextmanager
    def traced(
        context: CLICommandContext, command: Command, options: Options, args: CLIArgs
    ) -> Iterator[None]:
        init_span_processor(
            trace.init_tracing(
                service_namespace=trace.service_namespace_from_config(
                    "", omd_config := get_omd_config(context.omd_root)
                ),
                service_name="cmk",
                service_instance_id=omd_site(),
                extra_resource_attributes=trace.resource_attributes_from_config(context.omd_root),
            ),
            exporter_from_config(
                exporter_log_level=logging.CRITICAL,
                config=trace.trace_send_config(omd_config),
            ),
        )
        with tracer.span(
            f"command[{command.name}]",
            attributes={
                "cmk.base.command.name": command.name,
                "cmk.base.command.args": repr((context.global_options, options, args)),
            },
            context=trace.extract_context_from_environment(dict(environ)),
        ):
            yield

    return traced


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
                    trace_command=tracing(os.environ),
                    crash_reporter_for=saving_crash_reporter,
                    enable_profiling=profiling.enable,
                    write_profile=profiling.output_profile,
                ),
            )
