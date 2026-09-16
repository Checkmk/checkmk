#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Future convention within all Checkmk modules for variable names:
#
# - host_name     - Monitoring name of a host (string)
# - node_name     - Name of cluster member (string)
# - cluster_name  - Name of a cluster (string)
# - realhost_name - Name of a *real* host, not a cluster (string)

import errno
import logging
import os
import sys
from logging.handlers import WatchedFileHandler
from pathlib import Path
from typing import override, Self

# Needs to be placed before cmk modules, because they are not available
# when executed as non site user.
try:
    OMD_ROOT = Path(os.environ["OMD_ROOT"])
except KeyError:
    sys.stderr.write("Checkmk can be used only as site user.\n")
    sys.exit(1)

import cmk.ccc.debug
import cmk.ccc.version as cmk_version
import cmk.ccc.version_info as cmk_version_info
from cmk import trace
from cmk.base.app import make_app
from cmk.ccc.exceptions import (
    MKBailOut,
    MKGeneralException,
    MKTerminate,
    raise_mkterminate_on_sigint,
)
from cmk.ccc.log import CMKFormatter
from cmk.ccc.site import get_omd_config, omd_site
from cmk.cli.engine.call import call
from cmk.cli.engine.modes import (
    discover_modes,
    general_options,
    Modes,
    Option,
    parse_general_options,
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
from cmk.utils import log
from cmk.utils.paths import profile_dir

from .arguments import InvalidArguments, parse, ShowHelp
from .modes import write_paged


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
    ) -> Self:
        return cls(
            crash_report_base_path=crash_report_base_path,
            crash_info=cls.make_crash_info(
                version_info,
                BaseDetails(
                    argv=sys.argv,
                    env=dict(os.environ),
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


def _generate_crash_report() -> CrashReport:
    """Save a crash report and return the message to print instead of a traceback"""
    return CrashReport.from_exception(
        crash_report_base_path=make_crash_report_base_path(OMD_ROOT),
        version_info=cmk_version_info.get_general_version_infos(OMD_ROOT),
    )


def main() -> int:

    root_logger = logging.getLogger("cmk")
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        # astrein: disable=logging-formatter
        logging.Formatter("[%(levelname)s] %(message)s")
    )
    root_logger.addHandler(handler)
    logger = root_logger.getChild("base")

    raise_mkterminate_on_sigint()

    init_span_processor(
        trace.init_tracing(
            service_namespace=trace.service_namespace_from_config(
                "", omd_config := get_omd_config(OMD_ROOT)
            ),
            service_name="cmk",
            service_instance_id=omd_site(),
            extra_resource_attributes=trace.resource_attributes_from_config(OMD_ROOT),
        ),
        exporter_from_config(
            exporter_log_level=logging.CRITICAL,
            config=trace.trace_send_config(omd_config),
        ),
    )

    def _enable_file_logging(path: str) -> None:
        """Log to a timestamped file instead of stderr (used e.g. by cron jobs)."""
        _path = Path(path)
        _path.parent.mkdir(parents=True, exist_ok=True)
        handler = WatchedFileHandler(_path)
        handler.setFormatter(CMKFormatter())
        del root_logger.handlers[:]  # Remove the default stream handler.
        root_logger.addHandler(handler)

    _log_file_option = Option(
        long_option="log-file",
        short_help="Log to the given file (with timestamps) instead of stderr",
        argument=True,
        argument_descr="PATH",
    )

    modes = Modes(
        plugins=discover_modes(),
        general_options=[*general_options(), _log_file_option],
    )

    parsed = parse(modes, sys.argv)
    if isinstance(parsed, InvalidArguments):
        sys.stdout.write(parsed.message)
        return 1

    for option, argument in parsed.options:
        if option.lstrip("-") == _log_file_option.long_option:
            _enable_file_logging(argument)
    global_options = parse_general_options(parsed.options)
    if global_options.verbosity:
        log.logger.setLevel(log.verbosity_to_log_level(global_options.verbosity))
    if global_options.debug:
        cmk.ccc.debug.enable()
    if global_options.profile:
        profiling.enable()
        log.logger.debug("Enabled profiling")

    try:
        if isinstance(parsed, ShowHelp):
            write_paged(modes.help())
            return 0

        return call(
            make_app(cmk_version.edition(OMD_ROOT)),
            parsed.mode,
            global_options,
            parsed.argument,
            parsed.options,
            parsed.arguments,
            trace.extract_context_from_environment(dict(os.environ)),
        )

    except MKTerminate:
        logger.error("<Interrupted>")  # noqa: TRY400
        return 1

    except (MKGeneralException, MKBailOut) as e:
        logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if cmk.ccc.debug.enabled():
            raise
        return 3

    except OSError as e:
        if e.errno == errno.EPIPE:
            # this is not an error, caller closes socket(s) and will kill cmk too
            return 4
        crash = _generate_crash_report()
        crash.save()
        logger.error(crash.render())  # noqa: TRY400
        if cmk.ccc.debug.enabled():
            raise
        return 1

    except Exception:
        crash = _generate_crash_report()
        crash.save()
        logger.error(crash.render())  # noqa: TRY400
        if cmk.ccc.debug.enabled():
            raise
        return 1

    finally:
        profiling.output_profile(profile_dir)
