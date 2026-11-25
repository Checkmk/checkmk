#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import rrdtool  # type: ignore[import-not-found]

omd_root = os.environ["OMD_ROOT"]
rrd_path = os.path.join(omd_root, "test.rrd")

# Choosing a time that is easy on the eyes on the terminal
# Fri Jul 14 04:40:00 CEST 2017
start = 1500000000

rrdtool.create(
    [
        rrd_path,
        "--start",
        str(start - 60),
        "--step",
        "10s",
        "DS:one:GAUGE:100:0:100000000",
        "RRA:AVERAGE:0.5:1:10",
        "RRA:AVERAGE:0.5:4:10",
    ]
)

for i in range(0, 401, 10):
    rrdtool.update([rrd_path, "-t", "one", "%i:%i" % (start + i, i)])
