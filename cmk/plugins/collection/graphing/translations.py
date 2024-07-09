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

translation_tcp_conn_stats_datapower_tcp = translations.Translation(
    name="tcp_conn_stats_datapower_tcp",
    check_commands=[
        translations.PassiveCheck("tcp_conn_stats"),
        translations.PassiveCheck("datapower_tcp"),
    ],
    translations={
        "BOUND": translations.RenameTo("tcp_bound"),
        "CLOSED": translations.RenameTo("tcp_closed"),
        "CLOSE_WAIT": translations.RenameTo("tcp_close_wait"),
        "CLOSING": translations.RenameTo("tcp_closing"),
        "ESTABLISHED": translations.RenameTo("tcp_established"),
        "FIN_WAIT1": translations.RenameTo("tcp_fin_wait1"),
        "FIN_WAIT2": translations.RenameTo("tcp_fin_wait2"),
        "IDLE": translations.RenameTo("tcp_idle"),
        "LAST_ACK": translations.RenameTo("tcp_last_ack"),
        "LISTEN": translations.RenameTo("tcp_listen"),
        "SYN_RECV": translations.RenameTo("tcp_syn_recv"),
        "SYN_SENT": translations.RenameTo("tcp_syn_sent"),
        "TIME_WAIT": translations.RenameTo("tcp_time_wait"),
    },
)

translation_fileinfo = translations.Translation(
    name="fileinfo",
    check_commands=[translations.PassiveCheck("fileinfo")],
    translations={"size": translations.RenameTo("file_size")},
)

translation_fileinfo_groups = translations.Translation(
    name="fileinfo_groups",
    check_commands=[translations.PassiveCheck("fileinfo_groups")],
    translations={
        "age_newest": translations.RenameTo("file_age_newest"),
        "age_oldest": translations.RenameTo("file_age_oldest"),
        "count": translations.RenameTo("file_count"),
        "size": translations.RenameTo("total_file_size"),
        "size_largest": translations.RenameTo("file_size_largest"),
        "size_smallest": translations.RenameTo("file_size_smallest"),
    },
)

translation_apache_status = translations.Translation(
    name="apache_status",
    check_commands=[translations.PassiveCheck("apache_status")],
    translations={
        "Uptime": translations.RenameTo("uptime"),
        "IdleWorkers": translations.RenameTo("idle_workers"),
        "BusyWorkers": translations.RenameTo("busy_workers"),
        "IdleServers": translations.RenameTo("idle_servers"),
        "BusyServers": translations.RenameTo("busy_servers"),
        "OpenSlots": translations.RenameTo("open_slots"),
        "TotalSlots": translations.RenameTo("total_slots"),
        "CPULoad": translations.RenameTo("load1"),
        "ReqPerSec": translations.RenameTo("requests_per_second"),
        "BytesPerSec": translations.RenameTo("data_transfer_rate"),
        "BytesPerReq": translations.RenameTo("request_transfer_rate"),
        "ConnsTotal": translations.RenameTo("connections"),
        "ConnsAsyncWriting": translations.RenameTo("connections_async_writing"),
        "ConnsAsyncKeepAlive": translations.RenameTo("connections_async_keepalive"),
        "ConnsAsyncClosing": translations.RenameTo("connections_async_closing"),
        "State_StartingUp": translations.RenameTo("apache_state_startingup"),
        "State_Waiting": translations.RenameTo("apache_state_waiting"),
        "State_Logging": translations.RenameTo("apache_state_logging"),
        "State_DNS": translations.RenameTo("apache_state_dns"),
        "State_SendingReply": translations.RenameTo("apache_state_sending_reply"),
        "State_ReadingRequest": translations.RenameTo("apache_state_reading_request"),
        "State_Closing": translations.RenameTo("apache_state_closing"),
        "State_IdleCleanup": translations.RenameTo("apache_state_idle_cleanup"),
        "State_Finishing": translations.RenameTo("apache_state_finishing"),
        "State_Keepalive": translations.RenameTo("apache_state_keep_alive"),
    },
)

translation_kernel = translations.Translation(
    name="kernel",
    check_commands=[translations.PassiveCheck("kernel")],
    translations={
        "ctxt": translations.RenameTo("context_switches"),
        "pgmajfault": translations.RenameTo("major_page_faults"),
        "processes": translations.RenameTo("process_creations"),
    },
)
