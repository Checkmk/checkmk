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
import getopt
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
from cmk import trace
from cmk.base import profiling
from cmk.base.app import make_app
from cmk.base.modes.call import call
from cmk.base.modes.check_mk import general_options
from cmk.base.modes.modes import (
    discover_modes,
    Modes,
    Option,
)
from cmk.ccc.exceptions import (
    MKBailOut,
    MKGeneralException,
    MKTerminate,
    raise_mkterminate_on_sigint,
)
from cmk.ccc.site import get_omd_config, omd_site
from cmk.crash import (
    ABCCrashReport,
    BaseDetails,
    CrashReportStore,
    make_crash_report_base_path,
    VersionInfo,
)
from cmk.trace.export import (
    exporter_from_config,
    init_span_processor,
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
        version_info=cmk_version.get_general_version_infos(OMD_ROOT),
    )


def main() -> int:

    root_logger = logging.getLogger("cmk")
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
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
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
        )
        del root_logger.handlers[:]  # Remove the default stream handler.
        root_logger.addHandler(handler)

    _log_file_option = Option(
        long_option="log-file",
        short_help="Log to the given file (with timestamps) instead of stderr",
        handler_function=_enable_file_logging,
        argument=True,
        argument_descr="PATH",
    )

    modes = Modes(
        plugins=discover_modes(),
        general_options=[*general_options(), _log_file_option],
    )

    try:
        opts, args = getopt.getopt(
            sys.argv[1:], modes.short_getopt_specs(), modes.long_getopt_specs()
        )
    except getopt.GetoptError as err:
        prog = sys.argv[0].split("/")[-1]
        sys.stdout.write(f"ERROR: {err} (see `{prog} --help` for valid options)\n")
        return 1

    # First load the general modifying options
    modes.process_general_options(opts)

    try:
        # Now find the requested mode and execute it
        mode_name, mode_args = None, None
        for o, a in opts:
            if modes.exists(o := o.lstrip("-")):
                mode_name, mode_args = o, a
                break

        if not opts and not args:
            sys.stdout.write(modes.help())
            return 0

        app = make_app(cmk_version.edition(OMD_ROOT))

        done, exit_status = False, 0
        trace_context = trace.extract_context_from_environment(dict(os.environ))
        if mode_name is not None and mode_args is not None:
            exit_status = call(app, modes.get(mode_name), mode_args, opts, args, trace_context)
            done = True

        # When no mode was found, Checkmk is running the "check" mode
        if not done:
            if (args and len(args) <= 2) or "--keepalive" in [o[0] for o in opts]:
                exit_status = call(app, modes.get("check"), None, opts, args, trace_context)
            else:
                sys.stdout.write(modes.help())
                exit_status = 0

        return exit_status

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
        profiling.output_profile()


if __name__ == "__main__":
    sys.exit(main())
