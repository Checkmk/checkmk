#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translation

translation_citrix_serverload = translation.Translation(
    name="citrix_serverload",
    check_commands=[translation.PassiveCheck("citrix_serverload")],
    translations={"perf": translation.RenamingAndScaling("citrix_load", 0.01)},
)

translation_genau_fan = translation.Translation(
    name="genau_fan",
    check_commands=[translation.PassiveCheck("genau_fan")],
    translations={"rpm": translation.Renaming("fan")},
)

translation_ibm_svc_nodestats_disk_latency = translation.Translation(
    name="ibm_svc_nodestats_disk_latency",
    check_commands=[translation.PassiveCheck("ibm_svc_nodestats_disk_latency")],
    translations={
        "read_latency": translation.Scaling(0.001),
        "write_latency": translation.Scaling(0.001),
    },
)
