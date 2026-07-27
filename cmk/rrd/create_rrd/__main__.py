#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: rrdtool is missing type hints
import argparse
import logging
import os
from pathlib import Path

import rrdtool  # type: ignore[import-not-found]

from .. import RRDPaths
from ._main import create_rrd


def main() -> None:
    parser = argparse.ArgumentParser(prog="cmk-create-rrd")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="set the logging level (default: INFO)",
    )
    args = parser.parse_args()
    logging.getLogger().setLevel(args.log_level)

    omd_root = Path(os.environ.get("OMD_ROOT", ""))
    create_rrd(rrdtool, omd_root, RRDPaths.from_omd_root(omd_root))


if __name__ == "__main__":
    main()
