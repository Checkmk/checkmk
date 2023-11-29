#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translation

translation_citrix_serverload = translation.Translation(
    "citrix_serverload",
    [translation.PassiveCheck("citrix_serverload")],
    {"perf": translation.RenamingAndScaling("citrix_load", 0.01)},
)

translation_genau_fan = translation.Translation(
    "genau_fan",
    [translation.PassiveCheck("genau_fan")],
    {"rpm": translation.Renaming("fan")},
)

translation_ibm_svc_nodestats_disk_latency = translation.Translation(
    "ibm_svc_nodestats_disk_latency",
    [translation.PassiveCheck("ibm_svc_nodestats_disk_latency")],
    {
        "read_latency": translation.Scaling(0.001),
        "write_latency": translation.Scaling(0.001),
    },
)
