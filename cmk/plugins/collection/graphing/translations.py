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
    check_commands=[
        translations.PassiveCheck("fileinfo"),
        translations.PassiveCheck("filestats_single"),
        translations.PassiveCheck("filestats"),
    ],
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

translation_adva_fsp_if = translations.Translation(
    name="adva_fsp_if",
    check_commands=[translations.PassiveCheck("adva_fsp_if")],
    translations={
        "input_power": translations.RenameTo("input_signal_power_dbm"),
        "output_power": translations.RenameTo("output_signal_power_dbm"),
    },
)

translation_allnet_ip_sensoric_tension = translations.Translation(
    name="allnet_ip_sensoric_tension",
    check_commands=[translations.PassiveCheck("allnet_ip_sensoric_tension")],
    translations={"tension": translations.RenameTo("voltage_percent")},
)

translation_apc_ats_output = translations.Translation(
    name="apc_ats_output",
    check_commands=[translations.PassiveCheck("apc_ats_output")],
    translations={
        "ampere": translations.RenameTo("current"),
        "load_perc": translations.RenameTo("output_load"),
        "volt": translations.RenameTo("voltage"),
        "watt": translations.RenameTo("power"),
    },
)

translation_apc_rackpdu_power = translations.Translation(
    name="apc_rackpdu_power",
    check_commands=[translations.PassiveCheck("apc_rackpdu_power")],
    translations={"amperage": translations.RenameTo("current")},
)

translation_apc_symmetra = translations.Translation(
    name="apc_symmetra",
    check_commands=[translations.PassiveCheck("apc_symmetra")],
    translations={
        "OutputLoad": translations.RenameTo("output_load"),
        "batcurr": translations.RenameTo("battery_current"),
        "capacity": translations.RenameTo("battery_capacity"),
        "runtime": translations.RenameToAndScaleBy(
            "lifetime_remaining",
            60,
        ),
        "systemp": translations.RenameTo("battery_temp"),
    },
)

translation_apc_symmetra_elphase = translations.Translation(
    name="apc_symmetra_elphase",
    check_commands=[translations.PassiveCheck("apc_symmetra_elphase")],
    translations={
        "OutputLoad": translations.RenameTo("output_load"),
        "batcurr": translations.RenameTo("battery_current"),
    },
)

translation_apc_symmetra_temp = translations.Translation(
    name="apc_symmetra_temp",
    check_commands=[translations.PassiveCheck("apc_symmetra_temp")],
    translations={"systemp": translations.RenameTo("battery_temp")},
)

translation_arcserve_backup = translations.Translation(
    name="arcserve_backup",
    check_commands=[translations.PassiveCheck("arcserve_backup")],
    translations={
        "dirs": translations.RenameTo("directories"),
        "files": translations.RenameTo("file_count"),
        "size": translations.RenameTo("backup_size"),
    },
)

translation_aws_elb_http_elb_aws_elb_http_backend_aws_elbv2_application_http_elb_aws_s3_requests_http_errors = translations.Translation(
    name="aws_elb_http_elb_aws_elb_http_backend_aws_elbv2_application_http_elb_aws_s3_requests_http_errors",
    check_commands=[
        translations.PassiveCheck("aws_elb_http_elb"),
        translations.PassiveCheck("aws_elb_http_backend"),
        translations.PassiveCheck("aws_elbv2_application_http_elb"),
        translations.PassiveCheck("aws_s3_requests_http_errors"),
    ],
    translations={
        "http_4xx_perc": translations.RenameTo("aws_http_4xx_perc"),
        "http_4xx_rate": translations.RenameTo("aws_http_4xx_rate"),
        "http_5xx_perc": translations.RenameTo("aws_http_5xx_perc"),
        "http_5xx_rate": translations.RenameTo("aws_http_5xx_rate"),
    },
)

translation_bluecoat_diskcpu = translations.Translation(
    name="bluecoat_diskcpu",
    check_commands=[translations.PassiveCheck("bluecoat_diskcpu")],
    translations={"value": translations.RenameTo("generic_util")},
)

translation_brocade_fcport = translations.Translation(
    name="brocade_fcport",
    check_commands=[translations.PassiveCheck("brocade_fcport")],
    translations={
        "c3discards": translations.RenameTo("fc_c3discards"),
        "in": translations.RenameTo("fc_rx_bytes"),
        "notxcredits": translations.RenameTo("fc_notxcredits"),
        "out": translations.RenameTo("fc_tx_bytes"),
        "rxcrcs": translations.RenameTo("fc_crc_errors"),
        "rxencinframes": translations.RenameTo("fc_encins"),
        "rxencoutframes": translations.RenameTo("fc_encouts"),
        "rxframes": translations.RenameTo("fc_rx_frames"),
        "txframes": translations.RenameTo("fc_tx_frames"),
    },
)

translation_brocade_mlx_module_cpu = translations.Translation(
    name="brocade_mlx_module_cpu",
    check_commands=[translations.PassiveCheck("brocade_mlx_module_cpu")],
    translations={
        "cpu_util1": translations.RenameTo("util1s"),
        "cpu_util300": translations.RenameTo("util5"),
        "cpu_util5": translations.RenameTo("util5s"),
        "cpu_util60": translations.RenameTo("util1"),
    },
)

translation_brocade_mlx_module_mem = translations.Translation(
    name="brocade_mlx_module_mem",
    check_commands=[translations.PassiveCheck("brocade_mlx_module_mem")],
    translations={"memused": translations.RenameTo("mem_used")},
)

translation_chrony = translations.Translation(
    name="chrony",
    check_commands=[translations.PassiveCheck("chrony")],
    translations={
        "offset": translations.RenameToAndScaleBy(
            "time_offset",
            0.001,
        )
    },
)

translation_cisco_asa_svcsessions = translations.Translation(
    name="cisco_asa_svcsessions",
    check_commands=[translations.PassiveCheck("cisco_asa_svcsessions")],
    translations={"active": translations.RenameTo("active_sessions")},
)

translation_cisco_cpu_memory_cisco_sys_mem = translations.Translation(
    name="cisco_cpu_memory_cisco_sys_mem",
    check_commands=[
        translations.PassiveCheck("cisco_cpu_memory"),
        translations.PassiveCheck("cisco_sys_mem"),
    ],
    translations={"mem_used": translations.RenameTo("mem_used_percent")},
)

translation_cisco_mem_cisco_mem_asa_cisco_mem_asa64 = translations.Translation(
    name="cisco_mem_cisco_mem_asa_cisco_mem_asa64",
    check_commands=[
        translations.PassiveCheck("cisco_mem"),
        translations.PassiveCheck("cisco_mem_asa"),
        translations.PassiveCheck("cisco_mem_asa64"),
    ],
    translations={
        "growth": translations.RenameTo("mem_growth"),
        "mem_used": translations.RenameTo("mem_used_percent"),
        "trend": translations.RenameTo("mem_trend"),
    },
)

translation_cisco_qos = translations.Translation(
    name="cisco_qos",
    check_commands=[translations.PassiveCheck("cisco_qos")],
    translations={
        "drop": translations.RenameToAndScaleBy(
            "qos_dropped_bits_rate",
            8,
        ),
        "post": translations.RenameToAndScaleBy(
            "qos_outbound_bits_rate",
            8,
        ),
    },
)

translation_cisco_wlc_clients = translations.Translation(
    name="cisco_wlc_clients",
    check_commands=[translations.PassiveCheck("cisco_wlc_clients")],
    translations={"clients": translations.RenameTo("connections")},
)

translation_cups_queues = translations.Translation(
    name="cups_queues",
    check_commands=[translations.PassiveCheck("cups_queues")],
    translations={"jobs": translations.RenameTo("printer_queue")},
)

translation_dell_powerconnect_cpu = translations.Translation(
    name="dell_powerconnect_cpu",
    check_commands=[translations.PassiveCheck("dell_powerconnect_cpu")],
    translations={
        "load": translations.RenameTo("util"),
        "loadavg 5m": translations.RenameTo("util5"),
        "loadavg 60s": translations.RenameTo("util1"),
    },
)

translation_dell_powerconnect_temp = translations.Translation(
    name="dell_powerconnect_temp",
    check_commands=[translations.PassiveCheck("dell_powerconnect_temp")],
    translations={"temperature": translations.RenameTo("temp")},
)

translation_filesystem_storages_df = translations.Translation(
    name="filesystem_storages_df",
    check_commands=[
        translations.PassiveCheck("df"),
        translations.PassiveCheck("db2_logsizes"),
        translations.PassiveCheck("esx_vsphere_datastores"),
        translations.PassiveCheck("netapp_ontap_aggr"),
        translations.PassiveCheck("vms_df"),
        translations.PassiveCheck("vms_diskstat_df"),
        translations.NagiosPlugin("disk"),
        translations.PassiveCheck("df_netapp"),
        translations.PassiveCheck("df_netapp32"),
        translations.PassiveCheck("zfsget"),
        translations.PassiveCheck("hr_fs"),
        translations.PassiveCheck("oracle_asm_diskgroup"),
        translations.PassiveCheck("esx_vsphere_counters_ramdisk"),
        translations.PassiveCheck("hitachi_hnas_span"),
        translations.PassiveCheck("hitachi_hnas_volume"),
        translations.PassiveCheck("hitachi_hnas_volume_virtual"),
        translations.PassiveCheck("ibm_svc_mdiskgrp"),
        translations.PassiveCheck("fast_lta_silent_cubes_capacity"),
        translations.PassiveCheck("fast_lta_volumes"),
        translations.PassiveCheck("libelle_business_shadow_archive_dir"),
        translations.PassiveCheck("netapp_ontap_luns"),
        translations.PassiveCheck("netapp_ontap_qtree_quota"),
        translations.PassiveCheck("emc_datadomain_fs"),
        translations.PassiveCheck("emc_isilon_quota"),
        translations.PassiveCheck("emc_isilon_ifs"),
        translations.PassiveCheck("3par_cpgs_usage"),
        translations.PassiveCheck("3par_capacity"),
        translations.PassiveCheck("3par_volumes"),
        translations.PassiveCheck("storeonce_clusterinfo_space"),
        translations.PassiveCheck("storeonce_servicesets_capacity"),
        translations.PassiveCheck("storeonce4x_appliances_storage"),
        translations.PassiveCheck("storeonce4x_cat_stores"),
        translations.PassiveCheck("numble_volumes"),
        translations.PassiveCheck("zpool"),
        translations.PassiveCheck("vnx_quotas"),
        translations.PassiveCheck("sap_hana_diskusage"),
        translations.PassiveCheck("fjdarye200_pools"),
        translations.PassiveCheck("dell_compellent_folder"),
        translations.PassiveCheck("nimble_volumes"),
        translations.PassiveCheck("ceph_df"),
        translations.PassiveCheck("kube_pvc"),
        translations.PassiveCheck("lvm_vgs"),
        translations.PassiveCheck("df_netscaler"),
        translations.PassiveCheck("prism_host_usage"),
        translations.PassiveCheck("prism_containers"),
        translations.PassiveCheck("prism_storage_pools"),
        translations.PassiveCheck("ucd_disk"),
        translations.PassiveCheck("hp_msa_volume_df"),
    ],
    translations={
        "fs_free": translations.ScaleBy(1048576),
        "fs_size": translations.ScaleBy(1048576),
        "fs_used": translations.ScaleBy(1048576),
        "growth": translations.RenameToAndScaleBy(
            "fs_growth",
            12.136296296296296,
        ),
        "overprovisioned": translations.ScaleBy(1048576),
        "reserved": translations.ScaleBy(1048576),
        "trend": translations.RenameToAndScaleBy(
            "fs_trend",
            12.136296296296296,
        ),
        "trend_hoursleft": translations.ScaleBy(3600),
        "uncommitted": translations.ScaleBy(1048576),
        "~(?!inodes_used|fs_size|growth|trend|reserved|fs_free|fs_provisioning|uncommitted|overprovisioned|dedup_rate|file_count|fs_used_percent).*$": translations.RenameToAndScaleBy(
            "fs_used",
            1048576,
        ),
    },
)

# translation for lib function check_diskstat_dict
# no new check plugins should be added here (see docstring for check_diskstat_dict_)
translation_disk_utilization_check_diskstat_dict = translations.Translation(
    name="disk_utilization_check_diskstat_dict",
    check_commands=[
        translations.PassiveCheck("diskstat_io"),
        translations.PassiveCheck("diskstat_io_director"),
        translations.PassiveCheck("diskstat_io_volumes"),
        translations.PassiveCheck("aws_ebs"),
        translations.PassiveCheck("aws_ec2_disk_io"),
        translations.PassiveCheck("aws_rds_disk_io"),
        translations.PassiveCheck("cadvisor_diskstat"),
        translations.PassiveCheck("scaleio_storage_pool_totalrw"),
        translations.PassiveCheck("scaleio_storage_pool_rebalancerw"),
        translations.PassiveCheck("scaleio_volume"),
        translations.PassiveCheck("ucd_diskio"),
        translations.PassiveCheck("winperf_phydisk"),
        translations.PassiveCheck("gcp_filestore_disk"),
        translations.PassiveCheck("gcp_sql_disk"),
        translations.PassiveCheck("esx_vsphere_counters_diskio"),
        translations.PassiveCheck("esx_vsphere_datastore_io"),
    ],
    translations={
        "disk_utilization": translations.ScaleBy(100.0),
    },
)

translation_disk_smb = translations.Translation(
    name="disk_smb",
    check_commands=[translations.ActiveCheck("disk_smb")],
    translations={"~.*": translations.RenameTo("fs_used")},
)

translation_diskstat_aix_diskiod = translations.Translation(
    name="diskstat_aix_diskiod",
    check_commands=[
        translations.PassiveCheck("diskstat"),
        translations.PassiveCheck("aix_diskiod"),
    ],
    translations={
        "disk_utilization": translations.ScaleBy(100.0),
        "read": translations.RenameTo("disk_read_throughput"),
        "write": translations.RenameTo("disk_write_throughput"),
    },
)

translation_docker_container_cpu_hr_cpu_bintec_cpu_esx_vsphere_hostsystem = (
    translations.Translation(
        name="docker_container_cpu_hr_cpu_bintec_cpu_esx_vsphere_hostsystem",
        check_commands=[
            translations.PassiveCheck("docker_container_cpu"),
            translations.PassiveCheck("hr_cpu"),
            translations.PassiveCheck("bintec_cpu"),
            translations.PassiveCheck("esx_vsphere_hostsystem"),
        ],
        translations={"avg": translations.RenameTo("util_average")},
    )
)

translation_docker_node_disk_usage = translations.Translation(
    name="docker_node_disk_usage",
    check_commands=[translations.PassiveCheck("docker_node_disk_usage")],
    translations={
        "active": translations.RenameTo("docker_active"),
        "count": translations.RenameTo("docker_count"),
        "reclaimable": translations.RenameTo("docker_reclaimable"),
        "size": translations.RenameTo("docker_size"),
    },
)

translation_docker_node_info_containers = translations.Translation(
    name="docker_node_info_containers",
    check_commands=[translations.PassiveCheck("docker_node_info_containers")],
    translations={
        "containers": translations.RenameTo("docker_all_containers"),
        "paused": translations.RenameTo("docker_paused_containers"),
        "running": translations.RenameTo("docker_running_containers"),
        "stopped": translations.RenameTo("docker_stopped_containers"),
    },
)

translation_docsis_channels_downstream = translations.Translation(
    name="docsis_channels_downstream",
    check_commands=[translations.PassiveCheck("docsis_channels_downstream")],
    translations={"power": translations.RenameTo("downstream_power")},
)

translation_docsis_channels_upstream = translations.Translation(
    name="docsis_channels_upstream",
    check_commands=[translations.PassiveCheck("docsis_channels_upstream")],
    translations={
        "active": translations.RenameTo("active_modems"),
        "codewords_corrected": translations.ScaleBy(100.0),
        "codewords_uncorrectable": translations.ScaleBy(100.0),
        "frequency": translations.ScaleBy(1000000.0),
        "registered": translations.RenameTo("registered_modems"),
        "total": translations.RenameTo("total_modems"),
        "util": translations.RenameTo("channel_utilization"),
    },
)

translation_emc_isilon_iops = translations.Translation(
    name="emc_isilon_iops",
    check_commands=[translations.PassiveCheck("emc_isilon_iops")],
    translations={"iops": translations.RenameTo("disk_ios")},
)

translation_disk_utilization_scale = translations.Translation(
    name="disk_utilization_scale",
    check_commands=[
        translations.PassiveCheck("emc_vplex_director_stats"),
        translations.PassiveCheck("emc_vplex_volumes"),
        translations.PassiveCheck("hp_msa_controller_io"),
        translations.PassiveCheck("hp_msa_disk_io"),
        translations.PassiveCheck("hp_msa_volume_io"),
        translations.PassiveCheck("arbor_peakflow_sp_disk_usage"),
        translations.PassiveCheck("arbor_peakflow_tms_disk_usage"),
        translations.PassiveCheck("arbor_pravail_disk_usage"),
    ],
    translations={"disk_utilization": translations.ScaleBy(100.0)},
)

translation_esx_vsphere_counters_diskio = translations.Translation(
    name="esx_vsphere_counters_diskio",
    check_commands=[translations.PassiveCheck("esx_vsphere_counters_diskio")],
    translations={
        "ios": translations.RenameTo("disk_ios"),
        "latency": translations.RenameTo("disk_latency"),
        "read": translations.RenameTo("disk_read_throughput"),
        "write": translations.RenameTo("disk_write_throughput"),
    },
)

translation_esx_vsphere_hostsystem_mem_usage_esx_vsphere_hostsystem_mem_usage_cluster_juniper_screenos_mem_juniper_trpz_mem = translations.Translation(
    name="esx_vsphere_hostsystem_mem_usage_esx_vsphere_hostsystem_mem_usage_cluster_juniper_screenos_mem_juniper_trpz_mem",
    check_commands=[
        translations.PassiveCheck("esx_vsphere_hostsystem_mem_usage"),
        translations.PassiveCheck("esx_vsphere_hostsystem_mem_usage_cluster"),
        translations.PassiveCheck("juniper_screenos_mem"),
        translations.PassiveCheck("juniper_trpz_mem"),
    ],
    translations={"usage": translations.RenameTo("mem_used")},
)


translation_f5_bigip_conns = translations.Translation(
    name="f5_bigip_conns",
    check_commands=[translations.PassiveCheck("f5_bigip_conns")],
    translations={
        "conns": translations.RenameTo("connections"),
        "ssl_conns": translations.RenameTo("connections_ssl"),
    },
)

translation_f5_bigip_interfaces = translations.Translation(
    name="f5_bigip_interfaces",
    check_commands=[translations.PassiveCheck("f5_bigip_interfaces")],
    translations={
        "bytes_in": translations.RenameTo("if_in_octets"),
        "bytes_out": translations.RenameTo("if_out_octets"),
    },
)

translation_f5_bigip_vserver = translations.Translation(
    name="f5_bigip_vserver",
    check_commands=[translations.PassiveCheck("f5_bigip_vserver")],
    translations={"conn_rate": translations.RenameTo("connections_rate")},
)

translation_fc_port = translations.Translation(
    name="fc_port",
    check_commands=[translations.PassiveCheck("fc_port")],
    translations={
        "c3discards": translations.RenameTo("fc_c3discards"),
        "in": translations.RenameTo("fc_rx_bytes"),
        "notxcredits": translations.RenameTo("fc_notxcredits"),
        "out": translations.RenameTo("fc_tx_bytes"),
        "rxcrcs": translations.RenameTo("fc_crc_errors"),
        "rxencoutframes": translations.RenameTo("fc_encouts"),
        "rxobjects": translations.RenameTo("fc_rx_frames"),
        "txobjects": translations.RenameTo("fc_tx_frames"),
    },
)

translation_fortigate_sessions_base = translations.Translation(
    name="fortigate_sessions_base",
    check_commands=[translations.PassiveCheck("fortigate_sessions_base")],
    translations={"session": translations.RenameTo("active_sessions")},
)

translation_h3c_lanswitch_cpu = translations.Translation(
    name="h3c_lanswitch_cpu",
    check_commands=[translations.PassiveCheck("h3c_lanswitch_cpu")],
    translations={"usage": translations.RenameTo("util")},
)

translation_hitachi_hnas_cifs = translations.Translation(
    name="hitachi_hnas_cifs",
    check_commands=[translations.PassiveCheck("hitachi_hnas_cifs")],
    translations={"users": translations.RenameTo("cifs_share_users")},
)

translation_hitachi_hnas_cpu = translations.Translation(
    name="hitachi_hnas_cpu",
    check_commands=[translations.PassiveCheck("hitachi_hnas_cpu")],
    translations={"cpu_util": translations.RenameTo("util")},
)

translation_hitachi_hnas_fan = translations.Translation(
    name="hitachi_hnas_fan",
    check_commands=[translations.PassiveCheck("hitachi_hnas_fan")],
    translations={"fanspeed": translations.RenameTo("fan")},
)

translation_hivemanager_devices = translations.Translation(
    name="hivemanager_devices",
    check_commands=[translations.PassiveCheck("hivemanager_devices")],
    translations={"clients_count": translations.RenameTo("connections")},
)

translation_host_ping_cluster = translations.Translation(
    name="host-ping-cluster",
    check_commands=[translations.HostCheckCommand("host-ping-cluster")],
    translations={
        "~.*pl": translations.RenameToAndScaleBy(
            "pl",
            0.001,
        ),
        "~.*rta": translations.RenameToAndScaleBy(
            "rta",
            0.001,
        ),
        "~.*rtmax": translations.RenameToAndScaleBy(
            "rtmax",
            0.001,
        ),
        "~.*rtmin": translations.RenameToAndScaleBy(
            "rtmin",
            0.001,
        ),
    },
)

translation_hp_blade_psu = translations.Translation(
    name="hp_blade_psu",
    check_commands=[translations.PassiveCheck("hp_blade_psu")],
    translations={"output": translations.RenameTo("power")},
)

translation_hp_procurve_mem_datapower_mem_ucd_mem_netscaler_mem_f5_bigip_mem_f5_bigip_mem_tmm = (
    translations.Translation(
        name="hp_procurve_mem_datapower_mem_ucd_mem_netscaler_mem_f5_bigip_mem_f5_bigip_mem_tmm",
        check_commands=[
            translations.PassiveCheck("hp_procurve_mem"),
            translations.PassiveCheck("datapower_mem"),
            translations.PassiveCheck("ucd_mem"),
            translations.PassiveCheck("netscaler_mem"),
            translations.PassiveCheck("f5_bigip_mem"),
            translations.PassiveCheck("f5_bigip_mem_tmm"),
        ],
        translations={"memory_used": translations.RenameTo("mem_used")},
    )
)

translation_hp_proliant_power = translations.Translation(
    name="hp_proliant_power",
    check_commands=[translations.PassiveCheck("hp_proliant_power")],
    translations={"watt": translations.RenameTo("power")},
)

translation_hpux_cpu_lparstat_aix_cpu_util_ucd_cpu_util_vms_cpu_vms_sys_util = (
    translations.Translation(
        name="hpux_cpu_lparstat_aix_cpu_util_ucd_cpu_util_vms_cpu_vms_sys_util",
        check_commands=[
            translations.PassiveCheck("hpux_cpu"),
            translations.PassiveCheck("lparstat_aix_cpu_util"),
            translations.PassiveCheck("ucd_cpu_util"),
            translations.PassiveCheck("vms_cpu"),
            translations.PassiveCheck("vms_sys_util"),
        ],
        translations={"wait": translations.RenameTo("io_wait")},
    )
)

translation_hpux_tunables_maxfiles_lim = translations.Translation(
    name="hpux_tunables_maxfiles_lim",
    check_commands=[translations.PassiveCheck("hpux_tunables_maxfiles_lim")],
    translations={"files": translations.RenameTo("files_open")},
)

translation_hpux_tunables_semmns = translations.Translation(
    name="hpux_tunables_semmns",
    check_commands=[translations.PassiveCheck("hpux_tunables_semmns")],
    translations={"entries": translations.RenameTo("semaphores")},
)

translation_hpux_tunables_shmseg = translations.Translation(
    name="hpux_tunables_shmseg",
    check_commands=[translations.PassiveCheck("hpux_tunables_shmseg")],
    translations={"segments": translations.RenameTo("shared_memory_segments")},
)

translation_http = translations.Translation(
    name="http",
    check_commands=[translations.ActiveCheck("http")],
    translations={
        "size": translations.RenameTo("response_size"),
        "time": translations.RenameTo("response_time"),
    },
)

translation_ibm_svc_host = translations.Translation(
    name="ibm_svc_host",
    check_commands=[translations.PassiveCheck("ibm_svc_host")],
    translations={
        "active": translations.RenameTo("hosts_active"),
        "degraded": translations.RenameTo("hosts_degraded"),
        "inactive": translations.RenameTo("hosts_inactive"),
        "offline": translations.RenameTo("hosts_offline"),
        "other": translations.RenameTo("hosts_other"),
    },
)

translation_ibm_svc_license = translations.Translation(
    name="ibm_svc_license",
    check_commands=[translations.PassiveCheck("ibm_svc_license")],
    translations={"licensed": translations.RenameTo("licenses")},
)

translation_ibm_svc_nodestats_cache_ibm_svc_systemstats_cache = translations.Translation(
    name="ibm_svc_nodestats_cache_ibm_svc_systemstats_cache",
    check_commands=[
        translations.PassiveCheck("ibm_svc_nodestats_cache"),
        translations.PassiveCheck("ibm_svc_systemstats_cache"),
    ],
    translations={
        "total_cache_pc": translations.RenameTo("total_cache_usage"),
        "write_cache_pc": translations.RenameTo("write_cache_usage"),
    },
)

translation_ibm_svc_systemstats_disk_latency = translations.Translation(
    name="ibm_svc_systemstats_disk_latency",
    check_commands=[translations.PassiveCheck("ibm_svc_systemstats_disk_latency")],
    translations={
        "read_latency": translations.ScaleBy(0.001),
        "write_latency": translations.ScaleBy(0.001),
    },
)

translation_ibm_svc_systemstats_iops_ibm_svc_nodestats_iops = translations.Translation(
    name="ibm_svc_systemstats_iops_ibm_svc_nodestats_iops",
    check_commands=[
        translations.PassiveCheck("ibm_svc_systemstats_iops"),
        translations.PassiveCheck("ibm_svc_nodestats_iops"),
    ],
    translations={
        "read": translations.RenameTo("disk_read_ios"),
        "write": translations.RenameTo("disk_write_ios"),
    },
)

translation_icmp = translations.Translation(
    name="icmp",
    check_commands=[translations.NagiosPlugin("icmp")],
    translations={
        "~.*rta": translations.ScaleBy(0.001),
        "~.*rtmax": translations.ScaleBy(0.001),
        "~.*rtmin": translations.ScaleBy(0.001),
    },
)

translation_ping_exe = translations.Translation(
    name="ping_exe",
    check_commands=[translations.NagiosPlugin("check_ping.exe")],
    translations={
        "~.*rta": translations.ScaleBy(0.001),
    },
)

translation_tcp_exe = translations.Translation(
    name="tcp_exe",
    check_commands=[translations.NagiosPlugin("check_tcp.exe")],
    translations={"time": translations.RenameTo("response_time")},
)

translation_icmp_host_ping_host_service_ping = translations.Translation(
    name="icmp_host-ping_host-service_ping",
    check_commands=[
        translations.ActiveCheck("icmp"),
        translations.HostCheckCommand("host-ping"),
        translations.HostCheckCommand("host-service"),
        translations.HostCheckCommand("ping"),
    ],
    translations={
        "rta": translations.ScaleBy(0.001),
        "rtmax": translations.ScaleBy(0.001),
        "rtmin": translations.ScaleBy(0.001),
    },
)

translation_drbd_disk = translations.Translation(
    name="drbd_disk",
    check_commands=[translations.PassiveCheck("drbd_disk")],
    translations={
        # orig values in check plug-in are measured in kb
        "read": translations.RenameToAndScaleBy("disk_read_throughput", 1000),
        "write": translations.RenameToAndScaleBy("disk_write_throughput", 1000),
    },
)

translation_drbd_net = translations.Translation(
    name="drbd_net",
    check_commands=[translations.PassiveCheck("drbd_net")],
    translations={
        # orig values in check plug-in are measured in kb
        "in": translations.RenameToAndScaleBy("if_in_bps", 8000),
        "out": translations.RenameToAndScaleBy("if_out_bps", 8000),
    },
)

translation_drbd_stats = translations.Translation(
    name="drbd_stats",
    check_commands=[translations.PassiveCheck("drbd_stats")],
    translations={
        # see related check plug-in drbd_stats: "ooo (out of sync)"
        "kb_out_of_sync": translations.ScaleBy(1024),
    },
)

translation_interfaces_aws_ec2_network_io_aws_rds_network_io_cadvisor_if_esx_vsphere_counters_if_esx_vsphere_counters_fritz_fritz_wan_if_hitachi_hnas_fc_if_hpux_if_huawei_osn_if_if64_lnx_if_mcdata_fcport_netapp_ontap_if_winperf_if_gcp_gce_network_azure_vm_network_io_azure_v2_vm_network_io_prism_host_networks = translations.Translation(
    name="interfaces_aws_ec2_network_io_aws_rds_network_io_cadvisor_if_esx_vsphere_counters_if_esx_vsphere_counters_fritz_fritz_wan_if_hitachi_hnas_fc_if_hpux_if_huawei_osn_if_if64_lnx_if_mcdata_fcport_netapp_ontap_if_winperf_if_gcp_gce_network_azure_vm_network_io_azure_v2_vm_network_io_prism_host_networks",
    check_commands=[
        translations.PassiveCheck("interfaces"),
        translations.PassiveCheck("aws_ec2_network_io"),
        translations.PassiveCheck("aws_rds_network_io"),
        translations.PassiveCheck("cadvisor_if"),
        translations.PassiveCheck("esx_vsphere_counters_if"),
        translations.PassiveCheck("esx_vsphere_counters"),
        translations.PassiveCheck("fritz"),
        translations.PassiveCheck("fritz_wan_if"),
        translations.PassiveCheck("hitachi_hnas_fc_if"),
        translations.PassiveCheck("hpux_if"),
        translations.PassiveCheck("huawei_osn_if"),
        translations.PassiveCheck("if64"),
        translations.PassiveCheck("lnx_if"),
        translations.PassiveCheck("mcdata_fcport"),
        translations.PassiveCheck("netapp_ontap_if"),
        translations.PassiveCheck("winperf_if"),
        translations.PassiveCheck("gcp_gce_network"),
        translations.PassiveCheck("azure_vm_network_io"),
        translations.PassiveCheck("azure_v2_vm_network_io"),
        translations.PassiveCheck("prism_host_networks"),
    ],
    translations={
        "in": translations.RenameToAndScaleBy(
            "if_in_bps",
            8,
        ),
        "inbcast": translations.RenameTo("if_in_bcast"),
        "indisc": translations.RenameTo("if_in_discards"),
        "inerr": translations.RenameTo("if_in_errors"),
        "inmcast": translations.RenameTo("if_in_mcast"),
        "innucast": translations.RenameTo("if_in_non_unicast"),
        "inucast": translations.RenameTo("if_in_unicast"),
        "out": translations.RenameToAndScaleBy(
            "if_out_bps",
            8,
        ),
        "outbcast": translations.RenameTo("if_out_bcast"),
        "outdisc": translations.RenameTo("if_out_discards"),
        "outerr": translations.RenameTo("if_out_errors"),
        "outmcast": translations.RenameTo("if_out_mcast"),
        "outnucast": translations.RenameTo("if_out_non_unicast"),
        "outucast": translations.RenameTo("if_out_unicast"),
        "total": translations.RenameToAndScaleBy(
            "if_total_bps",
            8,
        ),
    },
)

translation_ipmi = translations.Translation(
    name="ipmi",
    check_commands=[translations.PassiveCheck("ipmi")],
    translations={"ambient_temp": translations.RenameTo("temp")},
)

translation_job = translations.Translation(
    name="job",
    check_commands=[translations.PassiveCheck("job")],
    translations={
        "reads": translations.RenameTo("disk_read_throughput"),
        "real_time": translations.RenameTo("job_duration"),
        "writes": translations.RenameTo("disk_write_throughput"),
    },
)

translation_jolokia_metrics_mem_jolokia_jvm_memory = translations.Translation(
    name="jolokia_metrics_mem_jolokia_jvm_memory",
    check_commands=[
        translations.PassiveCheck("jolokia_metrics_mem"),
        translations.PassiveCheck("jolokia_jvm_memory"),
    ],
    translations={
        "heap": translations.RenameToAndScaleBy(
            "mem_heap",
            1048576,
        ),
        "nonheap": translations.RenameToAndScaleBy(
            "mem_nonheap",
            1048576,
        ),
    },
)

translation_jolokia_metrics_threads = translations.Translation(
    name="jolokia_metrics_threads",
    check_commands=[translations.PassiveCheck("jolokia_metrics_threads")],
    translations={
        "DeamonThreadCount": translations.RenameTo("threads_daemon"),
        "PeakThreadCount": translations.RenameTo("threads_max"),
        "ThreadCount": translations.RenameTo("threads"),
        "ThreadRate": translations.RenameTo("threads_rate"),
        "TotalStartedThreadCount": translations.RenameTo("threads_total"),
    },
)

translation_jolokia_metrics_tp = translations.Translation(
    name="jolokia_metrics_tp",
    check_commands=[translations.PassiveCheck("jolokia_metrics_tp")],
    translations={
        "currentThreadCount": translations.RenameTo("threads_idle"),
        "currentThreadsBusy": translations.RenameTo("threads_busy"),
    },
)

translation_kernel_util_statgrab_cpu_lxc_container_cpu_emc_ecs_cpu_util = translations.Translation(
    name="kernel_util_statgrab_cpu_lxc_container_cpu_emc_ecs_cpu_util",
    check_commands=[
        translations.PassiveCheck("kernel_util"),
        translations.PassiveCheck("statgrab_cpu"),
        translations.PassiveCheck("lxc_container_cpu"),
        translations.PassiveCheck("emc_ecs_cpu_util"),
    ],
    translations={
        "guest": translations.RenameTo("cpu_util_guest"),
        "steal": translations.RenameTo("cpu_util_steal"),
        "wait": translations.RenameTo("io_wait"),
    },
)

translation_lparstat_aix = translations.Translation(
    name="lparstat_aix",
    check_commands=[translations.PassiveCheck("lparstat_aix")],
    translations={
        "sys": translations.RenameTo("system"),
        "wait": translations.RenameTo("io_wait"),
    },
)

translation_mail_loop = translations.Translation(
    name="mail_loop",
    check_commands=[translations.ActiveCheck("mail_loop")],
    translations={"duration": translations.RenameTo("mails_received_time")},
)

translation_mbg_lantime_state_mbg_lantime_ng_state = translations.Translation(
    name="mbg_lantime_state_mbg_lantime_ng_state",
    check_commands=[
        translations.PassiveCheck("mbg_lantime_state"),
        translations.PassiveCheck("mbg_lantime_ng_state"),
    ],
    translations={
        "offset": translations.RenameToAndScaleBy(
            "time_offset",
            1e-06,
        )
    },
)

translation_mem_linux = translations.Translation(
    name="mem_linux",
    check_commands=[translations.PassiveCheck("mem_linux")],
    translations={
        "active": translations.RenameTo("mem_lnx_active"),
        "active_anon": translations.RenameTo("mem_lnx_active_anon"),
        "active_file": translations.RenameTo("mem_lnx_active_file"),
        "anon_huge_pages": translations.RenameTo("mem_lnx_anon_huge_pages"),
        "anon_pages": translations.RenameTo("mem_lnx_anon_pages"),
        "bounce": translations.RenameTo("mem_lnx_bounce"),
        "buffers": translations.RenameTo("mem_lnx_buffers"),
        "cached": translations.RenameTo("mem_lnx_cached"),
        "caches": translations.RenameTo("caches"),
        "commit_limit": translations.RenameTo("mem_lnx_commit_limit"),
        "committed_as": translations.RenameTo("mem_lnx_committed_as"),
        "dirty": translations.RenameTo("mem_lnx_dirty"),
        "hardware_corrupted": translations.RenameTo("mem_lnx_hardware_corrupted"),
        "huge_pages_free": translations.RenameTo("mem_lnx_huge_pages_free"),
        "huge_pages_rsvd": translations.RenameTo("mem_lnx_huge_pages_rsvd"),
        "huge_pages_surp": translations.RenameTo("mem_lnx_huge_pages_surp"),
        "huge_pages_total": translations.RenameTo("mem_lnx_huge_pages_total"),
        "inactive": translations.RenameTo("mem_lnx_inactive"),
        "inactive_anon": translations.RenameTo("mem_lnx_inactive_anon"),
        "inactive_file": translations.RenameTo("mem_lnx_inactive_file"),
        "kernel_stack": translations.RenameTo("mem_lnx_kernel_stack"),
        "mapped": translations.RenameTo("mem_lnx_mapped"),
        "mem_free": translations.RenameTo("mem_free"),
        "mlocked": translations.RenameTo("mem_lnx_mlocked"),
        "nfs_unstable": translations.RenameTo("mem_lnx_nfs_unstable"),
        "page_tables": translations.RenameTo("mem_lnx_page_tables"),
        "pending": translations.RenameTo("mem_lnx_pending"),
        "shmem": translations.RenameTo("mem_lnx_shmem"),
        "slab": translations.RenameTo("mem_lnx_slab"),
        "swap_free": translations.RenameTo("swap_free"),
        "total_total": translations.RenameTo("mem_lnx_total_total"),
        "total_used": translations.RenameTo("mem_lnx_total_used"),
        "unevictable": translations.RenameTo("mem_lnx_unevictable"),
        "vmalloc_chunk": translations.RenameTo("mem_lnx_vmalloc_chunk"),
        "vmalloc_total": translations.RenameTo("mem_lnx_vmalloc_total"),
        "vmalloc_used": translations.RenameTo("mem_lnx_vmalloc_used"),
        "writeback": translations.RenameTo("mem_lnx_writeback"),
        "writeback_tmp": translations.RenameTo("mem_lnx_writeback_tmp"),
    },
)

translation_mem_vmalloc = translations.Translation(
    name="mem_vmalloc",
    check_commands=[translations.PassiveCheck("mem_vmalloc")],
    translations={
        "chunk": translations.RenameTo("mem_lnx_vmalloc_chunk"),
        "used": translations.RenameTo("mem_lnx_vmalloc_used"),
    },
)

translation_mem_win = translations.Translation(
    name="mem_win",
    check_commands=[translations.PassiveCheck("mem_win")],
    translations={
        "mem_total": translations.ScaleBy(1048576),
        "memory": translations.RenameToAndScaleBy(
            "mem_used",
            1048576,
        ),
        "memory_avg": translations.RenameToAndScaleBy(
            "mem_used_avg",
            1048576,
        ),
        "pagefile": translations.RenameToAndScaleBy(
            "pagefile_used",
            1048576,
        ),
        "pagefile_avg": translations.RenameToAndScaleBy(
            "pagefile_used_avg",
            1048576,
        ),
        "pagefile_total": translations.ScaleBy(1048576),
    },
)

translation_mgmt_ipmi_sensors_ipmi_sensors = translations.Translation(
    name="mgmt_ipmi_sensors_ipmi_sensors",
    check_commands=[
        translations.PassiveCheck("mgmt_ipmi_sensors"),
        translations.PassiveCheck("ipmi_sensors"),
    ],
    translations={"value": translations.RenameTo("temp")},
)

translation_mq_queues = translations.Translation(
    name="mq_queues",
    check_commands=[translations.PassiveCheck("mq_queues")],
    translations={"queue": translations.RenameTo("messages_in_queue")},
)

translation_mssql_counters_file_sizes = translations.Translation(
    name="mssql_counters_file_sizes",
    check_commands=[translations.PassiveCheck("mssql_counters_file_sizes")],
    translations={"log_files": translations.RenameTo("log_files_total")},
)

translation_mssql_counters_locks = translations.Translation(
    name="mssql_counters_locks",
    check_commands=[translations.PassiveCheck("mssql_counters_locks")],
    translations={
        "lock_requests/sec": translations.RenameTo("lock_requests_per_second"),
        "lock_timeouts/sec": translations.RenameTo("lock_timeouts_per_second"),
        "lock_waits/sec": translations.RenameTo("lock_waits_per_second"),
        "number_of_deadlocks/sec": translations.RenameTo("number_of_deadlocks_per_second"),
    },
)

translation_mssql_counters_pageactivity = translations.Translation(
    name="mssql_counters_pageactivity",
    check_commands=[translations.PassiveCheck("mssql_counters_pageactivity")],
    translations={
        "page_lookups/sec": translations.RenameTo("page_lookups_per_second"),
        "page_reads/sec": translations.RenameTo("page_reads_per_second"),
        "page_writes/sec": translations.RenameTo("page_writes_per_second"),
    },
)

translation_mssql_counters_sqlstats = translations.Translation(
    name="mssql_counters_sqlstats",
    check_commands=[translations.PassiveCheck("mssql_counters_sqlstats")],
    translations={
        "batch_requests/sec": translations.RenameTo("requests_per_second"),
        "sql_compilations/sec": translations.RenameTo("requests_per_second"),
        "sql_re-compilations/sec": translations.RenameTo("requests_per_second"),
    },
)

translation_mssql_counters_transactions = translations.Translation(
    name="mssql_counters_transactions",
    check_commands=[translations.PassiveCheck("mssql_counters_transactions")],
    translations={
        "tracked_transactions/sec": translations.RenameTo("tracked_transactions_per_second"),
        "transactions/sec": translations.RenameTo("transactions_per_second"),
        "write_transactions/sec": translations.RenameTo("write_transactions_per_second"),
    },
)

translation_mssql_tablespaces = translations.Translation(
    name="mssql_tablespaces",
    check_commands=[translations.PassiveCheck("mssql_tablespaces")],
    translations={
        "data": translations.RenameTo("data_size"),
        "indexes": translations.RenameTo("indexes_size"),
        "reserved": translations.RenameTo("reserved_size"),
        "size": translations.RenameTo("database_size"),
        "unallocated": translations.RenameTo("unallocated_size"),
        "unused": translations.RenameTo("unused_size"),
    },
)

translation_netapp_ontap_disk_summary = translations.Translation(
    name="netapp_ontap_disk_summary",
    check_commands=[translations.PassiveCheck("netapp_ontap_disk_summary")],
    translations={
        "total_disk_capacity": translations.RenameTo("disk_capacity"),
        "total_disks": translations.RenameTo("disks"),
    },
)

translation_netapp_ontap_volumes = translations.Translation(
    name="netapp_ontap_volumes",
    check_commands=[translations.PassiveCheck("netapp_ontap_volumes")],
    translations={
        "cifs_other_latency": translations.ScaleBy(0.001),
        "cifs_read_latency": translations.ScaleBy(0.001),
        "cifs_write_latency": translations.ScaleBy(0.001),
        "fcp_other_latency": translations.ScaleBy(0.001),
        "fcp_read_latency": translations.ScaleBy(0.001),
        "fcp_write_latency": translations.ScaleBy(0.001),
        "fs_free": translations.ScaleBy(1048576),
        "fs_size": translations.ScaleBy(1048576),
        "fs_used": translations.ScaleBy(1048576),
        "growth": translations.RenameToAndScaleBy(
            "fs_growth",
            12.136296296296296,
        ),
        "iscsi_other_latency": translations.ScaleBy(0.001),
        "iscsi_read_latency": translations.ScaleBy(0.001),
        "iscsi_write_latency": translations.ScaleBy(0.001),
        "nfs_other_latency": translations.ScaleBy(0.001),
        "nfs_read_latency": translations.ScaleBy(0.001),
        "nfs_write_latency": translations.ScaleBy(0.001),
        "other_latency": translations.ScaleBy(0.001),
        "read_latency": translations.ScaleBy(0.001),
        "san_other_latency": translations.ScaleBy(0.001),
        "san_read_latency": translations.ScaleBy(0.001),
        "san_write_latency": translations.ScaleBy(0.001),
        "trend": translations.RenameToAndScaleBy(
            "fs_trend",
            12.136296296296296,
        ),
        "write_latency": translations.ScaleBy(0.001),
    },
)

translation_nfsiostat = translations.Translation(
    name="nfsiostat",
    check_commands=[translations.PassiveCheck("nfsiostat")],
    translations={
        "read_avg_exe_ms": translations.RenameToAndScaleBy(
            "read_avg_exe_s",
            0.001,
        ),
        "read_avg_rtt_ms": translations.RenameToAndScaleBy(
            "read_avg_rtt_s",
            0.001,
        ),
        "write_avg_exe_ms": translations.RenameToAndScaleBy(
            "write_avg_exe_s",
            0.001,
        ),
        "write_avg_rtt_ms": translations.RenameToAndScaleBy(
            "write_avg_rtt_s",
            0.001,
        ),
    },
)

translation_ntp_ntp_time = translations.Translation(
    name="ntp_ntp_time",
    check_commands=[
        translations.PassiveCheck("ntp"),
        translations.PassiveCheck("ntp_time"),
    ],
    translations={
        "jitter": translations.ScaleBy(0.001),
        "offset": translations.RenameToAndScaleBy(
            "time_offset",
            0.001,
        ),
    },
)

translation_openbsd_sensors = translations.Translation(
    name="openbsd_sensors",
    check_commands=[translations.PassiveCheck("openbsd_sensors")],
    translations={"rpm": translations.RenameTo("fan")},
)

translation_openvpn_clients = translations.Translation(
    name="openvpn_clients",
    check_commands=[translations.PassiveCheck("openvpn_clients")],
    translations={
        "in": translations.RenameTo("if_in_octets"),
        "out": translations.RenameTo("if_out_octets"),
    },
)

translation_oracle_dataguard_stats = translations.Translation(
    name="oracle_dataguard_stats",
    check_commands=[translations.PassiveCheck("oracle_dataguard_stats")],
    translations={"apply_lag": translations.RenameTo("database_apply_lag")},
)

translation_oracle_jobs = translations.Translation(
    name="oracle_jobs",
    check_commands=[translations.PassiveCheck("oracle_jobs")],
    translations={"duration": translations.RenameTo("job_duration")},
)

translation_oracle_logswitches = translations.Translation(
    name="oracle_logswitches",
    check_commands=[translations.PassiveCheck("oracle_logswitches")],
    translations={"logswitches": translations.RenameTo("logswitches_last_hour")},
)

translation_oracle_longactivesessions = translations.Translation(
    name="oracle_longactivesessions",
    check_commands=[translations.PassiveCheck("oracle_longactivesessions")],
    translations={"count": translations.RenameTo("oracle_count")},
)

translation_oracle_performance = translations.Translation(
    name="oracle_performance",
    check_commands=[translations.PassiveCheck("oracle_performance")],
    translations={
        "DB_CPU": translations.RenameTo("oracle_db_cpu"),
        "DB_time": translations.RenameTo("oracle_db_time"),
        "buffer_busy_wait": translations.RenameTo("oracle_buffer_busy_wait"),
        "buffer_hit_ratio": translations.RenameTo("oracle_buffer_hit_ratio"),
        "consistent_gets": translations.RenameTo("oracle_db_block_gets"),
        "db_block_change": translations.RenameTo("oracle_db_block_change"),
        "db_block_gets": translations.RenameTo("oracle_db_block_gets"),
        "free_buffer_wait": translations.RenameTo("oracle_free_buffer_wait"),
        "library_cache_hit_ratio": translations.RenameTo("oracle_library_cache_hit_ratio"),
        "physical_reads": translations.RenameTo("oracle_physical_reads"),
        "physical_writes": translations.RenameTo("oracle_physical_writes"),
        "pinhitssum": translations.RenameTo("oracle_pin_hits_sum"),
        "pinssum": translations.RenameTo("oracle_pins_sum"),
    },
)

translation_oracle_recovery_area = translations.Translation(
    name="oracle_recovery_area",
    check_commands=[translations.PassiveCheck("oracle_recovery_area")],
    translations={
        "reclaimable": translations.RenameToAndScaleBy(
            "database_reclaimable",
            1048576,
        ),
        "used": translations.RenameToAndScaleBy(
            "database_size",
            1048576,
        ),
    },
)

translation_oracle_rman = translations.Translation(
    name="oracle_rman",
    check_commands=[translations.PassiveCheck("oracle_rman")],
    translations={"age": translations.RenameTo("backup_age")},
)

translation_oracle_sessions = translations.Translation(
    name="oracle_sessions",
    check_commands=[translations.PassiveCheck("oracle_sessions")],
    translations={"sessions": translations.RenameTo("running_sessions")},
)

translation_oracle_tablespaces = translations.Translation(
    name="oracle_tablespaces",
    check_commands=[translations.PassiveCheck("oracle_tablespaces")],
    translations={
        "max_size": translations.RenameTo("tablespace_max_size"),
        "size": translations.RenameTo("tablespace_size"),
        "used": translations.RenameTo("tablespace_used"),
    },
)

translation_ping = translations.Translation(
    name="ping",
    check_commands=[translations.NagiosPlugin("ping")],
    translations={"~.*rta": translations.ScaleBy(0.001)},
)

translation_postfix_mailq = translations.Translation(
    name="postfix_mailq",
    check_commands=[translations.PassiveCheck("postfix_mailq")],
    translations={
        "length": translations.RenameTo("mail_queue_deferred_length"),
        "size": translations.RenameTo("mail_queue_deferred_size"),
        "~mail_queue_.*_length": translations.RenameTo("mail_queue_active_length"),
        "~mail_queue_.*_size": translations.RenameTo("mail_queue_active_size"),
    },
)

translation_postgres_sessions = translations.Translation(
    name="postgres_sessions",
    check_commands=[translations.PassiveCheck("postgres_sessions")],
    translations={
        "running": translations.RenameTo("running_sessions"),
        "total": translations.RenameTo("total_sessions"),
    },
)

translation_postgres_stat_database_size = translations.Translation(
    name="postgres_stat_database_size",
    check_commands=[translations.PassiveCheck("postgres_stat_database_size")],
    translations={"size": translations.RenameTo("database_size")},
)

translation_printer_pages = translations.Translation(
    name="printer_pages",
    check_commands=[translations.PassiveCheck("printer_pages")],
    translations={"pages": translations.RenameTo("pages_total")},
)

translation_ps = translations.Translation(
    name="ps",
    check_commands=[translations.PassiveCheck("ps")],
    translations={
        "count": translations.RenameTo("processes"),
        "pcpu": translations.RenameTo("util"),
        "pcpuavg": translations.RenameTo("util_average"),
        "rss": translations.RenameToAndScaleBy(
            "process_resident_size",
            1024,
        ),
        "rssavg": translations.RenameToAndScaleBy(
            "process_resident_size_avg",
            1,
        ),
        "vsz": translations.RenameToAndScaleBy(
            "process_virtual_size",
            1024,
        ),
        "vszavg": translations.RenameToAndScaleBy(
            "process_virtual_size_avg",
            1,
        ),
    },
)

translation_pure_storage_fa_arrays_pure_storage_fa_volumes = translations.Translation(
    name="pure_storage_fa_arrays_pure_storage_fa_volumes",
    check_commands=[
        translations.PassiveCheck("pure_storage_fa_arrays"),
        translations.PassiveCheck("pure_storage_fa_volumes"),
    ],
    translations={
        "fs_free": translations.ScaleBy(1048576),
        "fs_used": translations.ScaleBy(1048576),
    },
)

translation_qlogic_fcport = translations.Translation(
    name="qlogic_fcport",
    check_commands=[translations.PassiveCheck("qlogic_fcport")],
    translations={
        "address_id_errors": translations.RenameTo("fc_address_id_errors"),
        "c2_fbsy_frames": translations.RenameTo("fc_c2_fbsy_frames"),
        "c2_frjt_frames": translations.RenameTo("fc_c2_frjt_frames"),
        "discards": translations.RenameTo("fc_c2c3_discards"),
        "in": translations.RenameTo("fc_rx_bytes"),
        "invalid_crcs": translations.RenameTo("fc_invalid_crcs"),
        "invalid_tx_words": translations.RenameTo("fc_invalid_tx_words"),
        "link_failures": translations.RenameTo("fc_link_fails"),
        "link_reset_ins": translations.RenameTo("fc_link_resets_in"),
        "link_reset_outs": translations.RenameTo("fc_link_resets_out"),
        "ols_ins": translations.RenameTo("fc_offline_seqs_in"),
        "ols_outs": translations.RenameTo("fc_offline_seqs_out"),
        "out": translations.RenameTo("fc_tx_bytes"),
        "prim_seq_proto_errors": translations.RenameTo("fc_prim_seq_errors"),
        "rxframes": translations.RenameTo("fc_rx_frames"),
        "sync_losses": translations.RenameTo("fc_sync_losses"),
        "txframes": translations.RenameTo("fc_tx_frames"),
    },
)

translation_raritan_pdu_outletcount = translations.Translation(
    name="raritan_pdu_outletcount",
    check_commands=[translations.PassiveCheck("raritan_pdu_outletcount")],
    translations={"outletcount": translations.RenameTo("connector_outlets")},
)

translation_rmon_stats = translations.Translation(
    name="rmon_stats",
    check_commands=[translations.PassiveCheck("rmon_stats")],
    translations={
        "0-63b": translations.RenameTo("rmon_packets_63"),
        "1024-1518b": translations.RenameTo("rmon_packets_1518"),
        "128-255b": translations.RenameTo("rmon_packets_255"),
        "256-511b": translations.RenameTo("rmon_packets_511"),
        "512-1023b": translations.RenameTo("rmon_packets_1023"),
        "64-127b": translations.RenameTo("rmon_packets_127"),
        "bcast": translations.RenameTo("broadcast_packets"),
        "mcast": translations.RenameTo("multicast_packets"),
    },
)

translation_sansymphony_pool = translations.Translation(
    name="sansymphony_pool",
    check_commands=[translations.PassiveCheck("sansymphony_pool")],
    translations={
        "fs_free": translations.ScaleBy(1048576),
        "fs_size": translations.ScaleBy(1048576),
        "fs_used": translations.ScaleBy(1048576),
        "growth": translations.RenameToAndScaleBy(
            "fs_growth",
            12.136296296296296,
        ),
        "overprovisioned": translations.ScaleBy(1048576),
        "percent_allocated": translations.RenameTo("fs_used_percent"),
        "reserved": translations.ScaleBy(1048576),
        "trend": translations.RenameToAndScaleBy(
            "fs_trend",
            12.136296296296296,
        ),
        "trend_hoursleft": translations.ScaleBy(3600),
        "uncommitted": translations.ScaleBy(1048576),
        "~(?!inodes_used|fs_size|growth|trend|reserved|fs_free|fs_provisioning|uncommitted|overprovisioned|dedup_rate|file_count|fs_used_percent).*$": translations.RenameToAndScaleBy(
            "fs_used",
            1048576,
        ),
    },
)

translation_smart_stats = translations.Translation(
    name="smart_stats",
    check_commands=[translations.PassiveCheck("smart_stats")],
    translations={
        "Available_Spare": translations.RenameTo("nvme_available_spare"),
        "CRC_Errors": translations.RenameTo("harddrive_crc_errors"),
        "CRC_Error_Count": translations.RenameTo("harddrive_crc_errors"),
        "Command_Timeout_Counter": translations.RenameTo("harddrive_cmd_timeouts"),
        "Critical_Warning": translations.RenameTo("nvme_critical_warning"),
        "Data_Units_Read": translations.RenameTo("nvme_data_units_read"),
        "Data_Units_Written": translations.RenameTo("nvme_data_units_written"),
        "End-to-End_Errors": translations.RenameTo("harddrive_end_to_end_errors"),
        "Error_Information_Log_Entries": translations.RenameTo(
            "nvme_error_information_log_entries"
        ),
        "Media_and_Data_Integrity_Errors": translations.RenameTo(
            "nvme_media_and_data_integrity_errors"
        ),
        "Pending_Sectors": translations.RenameTo("harddrive_pending_sectors"),
        "Percentage_Used": translations.RenameTo("nvme_spare_percentage_used"),
        "Power_Cycles": translations.RenameTo("harddrive_power_cycles"),
        "Power_On_Hours": translations.RenameToAndScaleBy(
            "uptime",
            3600,
        ),
        "Reallocated_Events": translations.RenameTo("harddrive_reallocated_events"),
        "Reallocated_Sectors": translations.RenameTo("harddrive_reallocated_sectors"),
        "Spin_Retries": translations.RenameTo("harddrive_spin_retries"),
        "UDMA_CRC_Errors": translations.RenameTo("harddrive_udma_crc_errors"),
        "Uncorrectable_Errors": translations.RenameTo("harddrive_uncorrectable_errors"),
    },
)

translation_statgrab_disk_ibm_svc_systemstats_diskio_ibm_svc_nodestats_diskio_mysql_innodb_io_netapp_fcpio = translations.Translation(
    name="statgrab_disk_ibm_svc_systemstats_diskio_ibm_svc_nodestats_diskio_mysql_innodb_io_netapp_fcpio",
    check_commands=[
        translations.PassiveCheck("statgrab_disk"),
        translations.PassiveCheck("ibm_svc_systemstats_diskio"),
        translations.PassiveCheck("ibm_svc_nodestats_diskio"),
        translations.PassiveCheck("mysql_innodb_io"),
        translations.PassiveCheck("netapp_fcpio"),
    ],
    translations={
        "read": translations.RenameTo("disk_read_throughput"),
        "write": translations.RenameTo("disk_write_throughput"),
    },
)

translation_statgrab_mem_hr_mem_solaris_mem_docker_container_mem_emc_ecs_mem_aix_memory_mem_used = (
    translations.Translation(
        name="statgrab_mem_hr_mem_solaris_mem_docker_container_mem_emc_ecs_mem_aix_memory_mem_used",
        check_commands=[
            translations.PassiveCheck("statgrab_mem"),
            translations.PassiveCheck("hr_mem"),
            translations.PassiveCheck("solaris_mem"),
            translations.PassiveCheck("docker_container_mem"),
            translations.PassiveCheck("emc_ecs_mem"),
            translations.PassiveCheck("aix_memory"),
            translations.PassiveCheck("mem_used"),
        ],
        translations={
            "committed_as": translations.RenameToAndScaleBy(
                "mem_lnx_committed_as",
                1048576,
            ),
            "mapped": translations.RenameToAndScaleBy(
                "mem_lnx_mapped",
                1048576,
            ),
            "memused": translations.RenameToAndScaleBy(
                "mem_lnx_total_used",
                1048576,
            ),
            "memusedavg": translations.RenameToAndScaleBy(
                "mem_used_avg",
                1048576,
            ),
            "pagetables": translations.RenameToAndScaleBy(
                "mem_lnx_page_tables",
                1048576,
            ),
            "ramused": translations.RenameToAndScaleBy(
                "mem_used",
                1048576,
            ),
            "shared": translations.RenameToAndScaleBy(
                "mem_lnx_shmem",
                1048576,
            ),
            "swapused": translations.RenameToAndScaleBy(
                "swap_used",
                1048576,
            ),
        },
    )
)

translation_steelhead_connections = translations.Translation(
    name="steelhead_connections",
    check_commands=[translations.PassiveCheck("steelhead_connections")],
    translations={
        "active": translations.RenameTo("fw_connections_active"),
        "established": translations.RenameTo("fw_connections_established"),
        "halfClosed": translations.RenameTo("fw_connections_halfclosed"),
        "halfOpened": translations.RenameTo("fw_connections_halfopened"),
        "passthrough": translations.RenameTo("fw_connections_passthrough"),
    },
)

translation_systemtime = translations.Translation(
    name="systemtime",
    check_commands=[translations.PassiveCheck("systemtime")],
    translations={"offset": translations.RenameTo("time_offset")},
)

translation_tcp_tcp_ldap_host_tcp = translations.Translation(
    name="tcp_tcp_ldap_host-tcp",
    check_commands=[
        translations.NagiosPlugin("tcp"),
        translations.ActiveCheck("tcp"),
        translations.ActiveCheck("ldap"),
        translations.HostCheckCommand("host-tcp"),
    ],
    translations={"time": translations.RenameTo("response_time")},
)

translation_tsm_stagingpools = translations.Translation(
    name="tsm_stagingpools",
    check_commands=[translations.PassiveCheck("tsm_stagingpools")],
    translations={
        "free": translations.RenameTo("tapes_free"),
        "tapes": translations.RenameTo("tapes_total"),
        "util": translations.RenameTo("tapes_util"),
    },
)

translation_tsm_storagepools = translations.Translation(
    name="tsm_storagepools",
    check_commands=[translations.PassiveCheck("tsm_storagepools")],
    translations={"used": translations.RenameTo("used_space")},
)

translation_ups_capacity = translations.Translation(
    name="ups_capacity",
    check_commands=[translations.PassiveCheck("ups_capacity")],
    translations={
        "capacity": translations.RenameTo("battery_seconds_remaining"),
        "percent": translations.RenameTo("battery_capacity"),
    },
)

translation_ups_out_load = translations.Translation(
    name="ups_out_load",
    check_commands=[translations.PassiveCheck("ups_out_load")],
    translations={
        "out_load": translations.RenameTo("output_load"),
        "out_voltage": translations.RenameTo("voltage"),
    },
)

translation_ups_socomec_out_voltage = translations.Translation(
    name="ups_socomec_out_voltage",
    check_commands=[translations.PassiveCheck("ups_socomec_out_voltage")],
    translations={"out_voltage": translations.RenameTo("voltage")},
)

translation_veeam_client = translations.Translation(
    name="veeam_client",
    check_commands=[translations.PassiveCheck("veeam_client")],
    translations={
        "avgspeed": translations.RenameTo("backup_avgspeed"),
        "duration": translations.RenameTo("backup_duration"),
        "totalsize": translations.RenameTo("backup_size"),
    },
)

translation_vms_system_ios = translations.Translation(
    name="vms_system_ios",
    check_commands=[translations.PassiveCheck("vms_system_ios")],
    translations={
        "buffered": translations.RenameTo("buffered_io"),
        "direct": translations.RenameTo("direct_io"),
    },
)

translation_vms_system_procs = translations.Translation(
    name="vms_system_procs",
    check_commands=[translations.PassiveCheck("vms_system_procs")],
    translations={"procs": translations.RenameTo("processes")},
)

translation_wagner_titanus_topsense_airflow_deviation = translations.Translation(
    name="wagner_titanus_topsense_airflow_deviation",
    check_commands=[translations.PassiveCheck("wagner_titanus_topsense_airflow_deviation")],
    translations={"airflow_deviation": translations.RenameTo("deviation_airflow")},
)

translation_wagner_titanus_topsense_chamber_deviation = translations.Translation(
    name="wagner_titanus_topsense_chamber_deviation",
    check_commands=[translations.PassiveCheck("wagner_titanus_topsense_chamber_deviation")],
    translations={"chamber_deviation": translations.RenameTo("deviation_calibration_point")},
)

translation_win_dhcp_pools = translations.Translation(
    name="win_dhcp_pools",
    check_commands=[translations.PassiveCheck("win_dhcp_pools")],
    translations={
        "free": translations.RenameTo("free_dhcp_leases"),
        "pending": translations.RenameTo("pending_dhcp_leases"),
        "used": translations.RenameTo("used_dhcp_leases"),
    },
)

translation_winperf_cpuusage = translations.Translation(
    name="winperf_cpuusage",
    check_commands=[translations.PassiveCheck("winperf_cpuusage")],
    translations={"cpuusage": translations.RenameTo("util")},
)

translation_winperf_processor_util = translations.Translation(
    name="winperf_processor_util",
    check_commands=[translations.PassiveCheck("winperf_processor_util")],
    translations={
        "avg": translations.RenameTo("util_average"),
        "util": translations.RenameTo("util_numcpu_as_max"),
    },
)

translation_zfs_arc_cache = translations.Translation(
    name="zfs_arc_cache",
    check_commands=[translations.PassiveCheck("zfs_arc_cache")],
    translations={
        "arc_meta_limit": translations.RenameTo("zfs_metadata_limit"),
        "arc_meta_max": translations.RenameTo("zfs_metadata_max"),
        "arc_meta_used": translations.RenameTo("zfs_metadata_used"),
        "hit_ratio": translations.RenameTo("cache_hit_ratio"),
        "size": translations.RenameTo("caches"),
    },
)

translation_zfs_arc_cache_l2 = translations.Translation(
    name="zfs_arc_cache_l2",
    check_commands=[translations.PassiveCheck("zfs_arc_cache_l2")],
    translations={
        "l2_hit_ratio": translations.RenameTo("zfs_l2_hit_ratio"),
        "l2_size": translations.RenameTo("zfs_l2_size"),
    },
)
