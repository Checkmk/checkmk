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

translation_db2_mem = translations.Translation(
    name="db2_mem",
    check_commands=[translations.PassiveCheck("db2_mem")],
    translations={"mem": translations.RenameTo("mem_used")},
)

translation_innovaphone_mem = translations.Translation(
    name="innovaphone_mem",
    check_commands=[translations.PassiveCheck("innovaphone_mem")],
    translations={"usage": translations.RenameTo("mem_used_percent")},
)

translation_arris_cmts_mem = translations.Translation(
    name="arris_cmts_mem",
    check_commands=[translations.PassiveCheck("arris_cmts_mem")],
    translations={"memused": translations.RenameTo("mem_used")},
)

translation_apc_mod_pdu_modules = translations.Translation(
    name="apc_mod_pdu_modules",
    check_commands=[translations.PassiveCheck("apc_mod_pdu_modules")],
    translations={"current_power": translations.RenameToAndScaleBy("power", 1000)},
)

translation_apc_inrow_airflow = translations.Translation(
    name="apc_inrow_airflow",
    check_commands=[translations.PassiveCheck("apc_inrow_airflow")],
    translations={"flow": translations.RenameTo("airflow")},
)

translation_apc_inrow_fanspeed = translations.Translation(
    name="apc_inrow_fanspeed",
    check_commands=[translations.PassiveCheck("apc_inrow_fanspeed")],
    translations={"fanspeed": translations.RenameTo("fan_perc")},
)
