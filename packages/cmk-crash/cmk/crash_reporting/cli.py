#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""CLI entrypoint `cmk-upload-crashes`: batch-upload pending crash reports."""

from __future__ import annotations

import os
import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from dataclasses import dataclass
from logging import DEBUG, Formatter, getLogger, INFO, StreamHandler
from pathlib import Path

from cmk.ccc.site import omd_site
from cmk.ccc.store import load_mk_file
from cmk.ccc.version import edition
from cmk.crash import make_crash_report_base_path

from .upload import run_batch

logger = getLogger("cmk.crash_reporting.cli")

# Matches ConfigVariableCrashReportURL's default (cmk/gui/general_config.py).
_DEFAULT_CRASH_REPORT_URL = "https://crash.checkmk.com"


@dataclass(slots=True)
class Arguments:
    dry_run: bool = False
    verbose: int = 0


def parse_arguments(argv: Sequence[str]) -> Arguments:
    p = ArgumentParser(description=__doc__)
    p.add_argument(
        "--dry-run", action="store_true", help="Log what would be uploaded, upload nothing"
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose mode (use multiple times for more output)",
    )
    return p.parse_args(argv, namespace=Arguments())


def setup_logging(*, verbose: int) -> None:
    getLogger("cmk").setLevel(INFO if verbose == 0 else DEBUG)
    handler = StreamHandler(sys.stderr)
    handler.setFormatter(Formatter("%(message)s"))
    getLogger().addHandler(handler)


def main() -> int:
    arguments = parse_arguments(sys.argv[1:])
    setup_logging(verbose=arguments.verbose)

    # Read OMD_ROOT directly instead of depending on cmk.utils.paths: this CLI
    # only ever needs the root path itself, and paths.py is one flat module
    # with no way to depend on just that one name.
    try:
        omd_root = Path(os.environ["OMD_ROOT"])
    except KeyError as exc:
        raise RuntimeError(
            "OMD_ROOT environment variable not set. Can only be executed in a Checkmk site."
        ) from exc

    settings = load_mk_file(
        omd_root / "etc/check_mk/multisite.d/wato/global.mk", default={}, lock=False
    )
    # global.mk is hand-editable and not owned by this CLI, so the GUI's valuespec is
    # the only thing keeping this a string. A stray truthy non-string would otherwise
    # pass as an address; anything but a non-empty string counts as "off".
    mail = settings.get("automatic_crash_report_upload")
    if not isinstance(mail, str) or not mail:
        logger.info("Automatic crash report upload is disabled - nothing to do.")
        return 0

    run_batch(
        crash_report_url=str(settings.get("crash_report_url", _DEFAULT_CRASH_REPORT_URL)),
        base_path=make_crash_report_base_path(omd_root),
        # Identify the sending site by edition + site name, rather than by a
        # user alias as the manual GUI submit does.
        name=f"{edition(omd_root).short} {omd_site()}",
        mail=mail,
        dry_run=arguments.dry_run,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
