#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import sys

import rrdtool  # type: ignore[import-not-found]

rrd_database, qstart, qend = ast.literal_eval(sys.stdin.read())

print(
    rrdtool.xport(
        [
            f"DEF:fir={rrd_database}:one:AVERAGE",
            "XPORT:fir",
            "-s",
            str(qstart),
            "-e",
            str(qend),
        ]
    )
)
