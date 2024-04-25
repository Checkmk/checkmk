#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translations

translation_citrix_serverload = translations.Translation(
    name="citrix_serverload",
    check_commands=[translations.PassiveCheck("citrix_serverload")],
    translations={"perf": translations.RenameToAndScaleBy("citrix_load", 0.01)},
)

translation_genau_fan = translations.Translation(
    name="genau_fan",
    check_commands=[translations.PassiveCheck("genau_fan")],
    translations={"rpm": translations.RenameTo("fan")},
)

translation_ibm_svc_nodestats_disk_latency = translations.Translation(
    name="ibm_svc_nodestats_disk_latency",
    check_commands=[translations.PassiveCheck("ibm_svc_nodestats_disk_latency")],
    translations={
        "read_latency": translations.ScaleBy(0.001),
        "write_latency": translations.ScaleBy(0.001),
    },
)

translation_winperf_msx_queues = translations.Translation(
    name="winperf_msx_queues",
    check_commands=[translations.PassiveCheck("winperf_msx_queues")],
    translations={"length": translations.RenameTo("queue_length")},
)

translation_emc_datadomain_nvbat = translations.Translation(
    name="emc_datadomain_nvbat",
    check_commands=[translations.PassiveCheck("emc_datadomain_nvbat")],
    translations={"charge": translations.RenameTo("battery_capacity")},
)
