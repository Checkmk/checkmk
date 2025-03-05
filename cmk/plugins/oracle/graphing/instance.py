#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_oracle_pdb_total_size = metrics.Metric(
    name="oracle_pdb_total_size",
    title=Title("Oracle PDB Total Size"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

perfometer_oracle_pdb_total_size = perfometers.Perfometer(
    name="oracle_pdb_total_size",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(1_000_000_000_000),
    ),
    segments=["oracle_pdb_total_size"],
)
