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

from cmk.rrd.create_rrd.main import create_rrd
from cmk.rrd.fs import RRDPaths
from cmk.utils.log import verbosity_to_log_level  # astrein: disable=cmk-module-layer-violation


def _set_log_level(verbosity: int) -> None:
    logging.getLogger().setLevel(verbosity_to_log_level(verbosity))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cmk-create-rrd",
    )
    parser.add_argument("-v", "--verbose", action="count", default=0)
    args = parser.parse_args()
    _set_log_level(args.verbose)

    omd_root = Path(os.environ.get("OMD_ROOT", ""))
    create_rrd(rrdtool, omd_root, RRDPaths.from_omd_root(omd_root))


if __name__ == "__main__":
    main()
