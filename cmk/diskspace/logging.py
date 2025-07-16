#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys

from cmk.diskspace.config import Config
from cmk.diskspace.free_space import fmt_bytes


def error(message: str) -> None:
    sys.stderr.write(f"ERROR: {message}\n")


def log(message: str) -> None:
    logging.getLogger(__name__).info(message)


def verbose(message: str) -> None:
    logging.getLogger(__name__).debug(message)


def setup_logging(is_verbose: bool) -> None:
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=logging.DEBUG if is_verbose else logging.INFO
    )


def print_config(config: Config) -> None:
    verbose("Settings:")
    if config.cleanup_abandoned_host_files is None:
        verbose("  Not cleaning up abandoned host files.")
    else:
        verbose(
            "  Cleaning up abandoned host files older than %d seconds."
            % int(config.cleanup_abandoned_host_files)
        )

    if config.max_file_age is None:
        verbose("  Not cleaning up files by age.")
    else:
        verbose("  Cleanup files that are older than %d seconds." % config.max_file_age)

    match config.min_free_bytes:
        case None:
            verbose("  Not cleaning up files by free space left.")
        case (bytes_, age):
            verbose(
                "  Cleanup files till %s are free while not deleting files "
                "older than %d seconds" % (fmt_bytes(bytes_), age)
            )
