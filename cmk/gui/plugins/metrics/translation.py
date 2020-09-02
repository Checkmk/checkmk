#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

from cmk.gui.plugins.metrics.utils import check_metrics, CheckMetricEntry, KB, m, MB

# .
#   .--Checks--------------------------------------------------------------.
#   |                    ____ _               _                            |
#   |                   / ___| |__   ___  ___| | _____                     |
#   |                  | |   | '_ \ / _ \/ __| |/ / __|                    |
#   |                  | |___| | | |  __/ (__|   <\__ \                    |
#   |                   \____|_| |_|\___|\___|_|\_\___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  How various checks' performance data translate into the known       |
#   |  metrics                                                             |
#   '----------------------------------------------------------------------'

check_metrics["check_mk_active-icmp"] = {
    "rta": {"scale": m},
    "rtmax": {"scale": m},
    "rtmin": {"scale": m},
}
# This metric is not for an official Checkmk check
# It may be provided by an check_icmp check configured as mrpe
check_metrics["check_icmp"] = {
    "~.*rta": {"scale": m},
    "~.*rtmax": {"scale": m},
    "~.*rtmin": {"scale": m},
}
check_metrics["check_tcp"] = {
    "time": {"name": "response_time"},
}
check_metrics["check-mk-host-ping"] = {
    "rta": {"scale": m},
    "rtmax": {"scale": m},
    "rtmin": {"scale": m},
}
check_metrics["check-mk-host-service"] = {
    "rta": {"scale": m},
    "rtmax": {"scale": m},
    "rtmin": {"scale": m},
}
check_metrics["check-mk-ping"] = {
    "rta": {"scale": m},
    "rtmax": {"scale": m},
    "rtmin": {"scale": m},
}
check_metrics["check-mk-host-ping-cluster"] = {
    "~.*rta": {"name": "rta", "scale": m},
    "~.*pl": {"name": "pl", "scale": m},
    "~.*rtmax": {"name": "rtmax", "scale": m},
    "~.*rtmin": {"name": "rtmin", "scale": m},
}
check_metrics["check_mk_active-mail_loop"] = {
    "duration": {"name": "mails_received_time"},
}
check_metrics["check_mk_active-http"] = {
    "time": {"name": "response_time"},
    "size": {"name": "response_size"},
}
check_metrics["check_mk_active-tcp"] = {
    "time": {"name": "response_time"},
}
check_metrics["check_mk_active-ldap"] = {
    "time": {"name": "response_time"},
}
check_metrics["check-mk-host-tcp"] = {
    "time": {"name": "response_time"},
}
for check in [
    "winperf_processor_util",
    "docker_container_cpu",
    "hr_cpu",
    "bintec_cpu",
    "esx_vsphere_hostsystem",
]:
    check_metrics["check_mk-%s" % check] = {
        "avg": {"name": "util_average"},
    }
check_metrics["check_mk-winperf_processor_util"].update({"util": {"name": "util_numcpu_as_max"}})
check_metrics["check_mk-netapp_api_cpu"] = {"util": {"name": "util_numcpu_as_max"}}
check_metrics["check_mk-netapp_api_cpu_utilization"] = {"util": {"name": "util_numcpu_as_max"}}
check_metrics["check_mk-citrix_serverload"] = {
    "perf": {"name": "citrix_load", "scale": 0.01},
}
check_metrics["check_mk-genau_fan"] = {
    "rpm": {"name": "fan"},
}
check_metrics["check_mk-openbsd_sensors"] = {
    "rpm": {"name": "fan"},
}
check_metrics["check_mk-postfix_mailq"] = {
    "length": {"name": "mail_queue_deferred_length"},
    "size": {"name": "mail_queue_deferred_size"},
    "~mail_queue_.*_size": {"name": "mail_queue_active_size"},
    "~mail_queue_.*_length": {"name": "mail_queue_active_length"},
}
check_metrics["check_mk-jolokia_metrics_gc"] = {
    "CollectionCount": {
        "name": "jvm_garbage_collection_count",
        "scale": 1 / 60.0,
    },
    "CollectionTime": {
        "name": "jvm_garbage_collection_time",
        "scale": 1 / 600.0,  # ms/min -> %
    },
}
check_metrics["check_mk-rmon_stats"] = {
    "bcast": {"name": "broadcast_packets"},
    "mcast": {"name": "multicast_packets"},
    "0-63b": {"name": "rmon_packets_63"},
    "64-127b": {"name": "rmon_packets_127"},
    "128-255b": {"name": "rmon_packets_255"},
    "256-511b": {"name": "rmon_packets_511"},
    "512-1023b": {"name": "rmon_packets_1023"},
    "1024-1518b": {"name": "rmon_packets_1518"},
}
check_metrics["check_mk-cpu_loads"] = {
    "load5": {"auto_graph": False},
}
check_metrics["check_mk-ucd_cpu_load"] = {
    "load5": {"auto_graph": False},
}
check_metrics["check_mk-statgrab_load"] = {
    "load5": {"auto_graph": False},
}
check_metrics["check_mk-hpux_cpu"] = {
    "wait": {"name": "io_wait"},
}
check_metrics["check_mk-hitachi_hnas_cpu"] = {
    "cpu_util": {"name": "util"},
}
check_metrics["check_mk-hitachi_hnas_cifs"] = {
    "users": {"name": "cifs_share_users"},
}
check_metrics["check_mk-hitachi_hnas_fan"] = {
    "fanspeed": {"name": "fan"},
}
check_metrics["check_mk-statgrab_disk"] = {
    "read": {"name": "disk_read_throughput"},
    "write": {"name": "disk_write_throughput"},
}
check_metrics["check_mk-ibm_svc_systemstats_diskio"] = {
    "read": {"name": "disk_read_throughput"},
    "write": {"name": "disk_write_throughput"},
}
check_metrics["check_mk-ibm_svc_nodestats_diskio"] = {
    "read": {"name": "disk_read_throughput"},
    "write": {"name": "disk_write_throughput"},
}
memory_simple_translation: Dict[str, CheckMetricEntry] = {
    "memory_used": {
        "name": "mem_used",
        "deprecated": "2.0.0i1",
    },
}
check_metrics["check_mk-hp_procurve_mem"] = memory_simple_translation
check_metrics["check_mk-datapower_mem"] = memory_simple_translation
check_metrics["check_mk-ucd_mem"] = memory_simple_translation
check_metrics["check_mk-netscaler_mem"] = memory_simple_translation
ram_used_swap_translation: Dict[str, CheckMetricEntry] = {
    "ramused": {
        "name": "mem_used",
        "scale": MB,
        "deprecated": "2.0.0i1",
    },
    "mem_used_percent": {
        "auto_graph": False,
    },
    "swapused": {
        "name": "swap_used",
        "scale": MB,
        "deprecated": "2.0.0i1",
    },
    "memused": {
        "name": "mem_lnx_total_used",
        "auto_graph": False,
        "scale": MB,
        "deprecated": "2.0.0i1",
    },
    "mem_lnx_total_used": {
        "auto_graph": False,
    },
    "memusedavg": {"name": "memory_avg", "scale": MB},
    "shared": {"name": "mem_lnx_shmem", "deprecated": "2.0.0i1", "scale": MB},
    "pagetables": {"name": "mem_lnx_page_tables", "deprecated": "2.0.0i1", "scale": MB},
    "mapped": {"name": "mem_lnx_mapped", "deprecated": "2.0.0i1", "scale": MB},
    "committed_as": {"name": "mem_lnx_committed_as", "deprecated": "2.0.0i1", "scale": MB},
}
check_metrics["check_mk-statgrab_mem"] = ram_used_swap_translation
check_metrics["check_mk-hr_mem"] = ram_used_swap_translation
check_metrics["check_mk-solaris_mem"] = ram_used_swap_translation
check_metrics["check_mk-docker_container_mem"] = ram_used_swap_translation
check_metrics["check_mk-emc_ecs_mem"] = ram_used_swap_translation
check_metrics["check_mk-aix_memory"] = ram_used_swap_translation
check_metrics["check_mk-mem_used"] = ram_used_swap_translation
check_metrics["check_mk-esx_vsphere_vm_mem_usage"] = {
    "host": {"name": "mem_esx_host"},
    "guest": {"name": "mem_esx_guest"},
    "ballooned": {"name": "mem_esx_ballooned"},
    "shared": {"name": "mem_esx_shared"},
    "private": {"name": "mem_esx_private"},
}
check_metrics["check_mk-ibm_svc_nodestats_disk_latency"] = {
    "read_latency": {"scale": m},
    "write_latency": {"scale": m},
}
check_metrics["check_mk-ibm_svc_systemstats_disk_latency"] = {
    "read_latency": {"scale": m},
    "write_latency": {"scale": m},
}
check_metrics["check_mk-netapp_api_disk_summary"] = {
    "total_disk_capacity": {"name": "disk_capacity"},
    "total_disks": {"name": "disks"},
}
check_metrics["check_mk-emc_isilon_iops"] = {
    "iops": {"name": "disk_ios"},
}
check_metrics["check_mk-vms_system_ios"] = {
    "direct": {"name": "direct_io"},
    "buffered": {"name": "buffered_io"},
}
check_metrics["check_mk-kernel"] = {
    "ctxt": {"name": "context_switches"},
    "pgmajfault": {"name": "major_page_faults"},
    "processes": {"name": "process_creations"},
}
check_metrics["check_mk-oracle_jobs"] = {
    "duration": {"name": "job_duration"},
}
check_metrics["check_mk-oracle_recovery_area"] = {
    "used": {"name": "database_size", "scale": MB},
    "reclaimable": {"name": "database_reclaimable", "scale": MB},
}
check_metrics["check_mk-vms_system_procs"] = {
    "procs": {"name": "processes"},
}
check_metrics["check_mk-jolokia_metrics_tp"] = {
    "currentThreadCount": {"name": "threads_idle"},
    "currentThreadsBusy": {"name": "threads_busy"},
}
check_metrics["check_mk-mem_win"] = {
    "memory": {"name": "mem_used", "scale": MB, "deprecated": "2.0.0i1"},
    "pagefile": {"name": "pagefile_used", "scale": MB},
    "memory_avg": {"scale": MB},
    "pagefile_avg": {"scale": MB},
    "mem_total": {"auto_graph": False, "scale": MB},
    "pagefile_total": {"auto_graph": False, "scale": MB},
}
check_metrics["check_mk-brocade_mlx_module_mem"] = {
    "memused": {
        "name": "mem_used",
        "deprecated": "2.0.0i1",
    },
}
check_metrics["check_mk-jolokia_metrics_mem"] = {
    "heap": {"name": "mem_heap", "scale": MB},
    "nonheap": {"name": "mem_nonheap", "scale": MB},
}
check_metrics["check_mk-jolokia_metrics_threads"] = {
    "ThreadRate": {"name": "threads_rate"},
    "ThreadCount": {"name": "threads"},
    "DeamonThreadCount": {"name": "threads_daemon"},
    "PeakThreadCount": {"name": "threads_max"},
    "TotalStartedThreadCount": {"name": "threads_total"},
}
check_metrics["check_mk-mem_linux"] = {
    "cached": {
        "name": "mem_lnx_cached",
    },
    "buffers": {
        "name": "mem_lnx_buffers",
    },
    "slab": {
        "name": "mem_lnx_slab",
    },
    "active_anon": {
        "name": "mem_lnx_active_anon",
    },
    "active_file": {
        "name": "mem_lnx_active_file",
    },
    "inactive_anon": {
        "name": "mem_lnx_inactive_anon",
    },
    "inactive_file": {
        "name": "mem_lnx_inactive_file",
    },
    "dirty": {
        "name": "mem_lnx_dirty",
    },
    "writeback": {
        "name": "mem_lnx_writeback",
    },
    "nfs_unstable": {
        "name": "mem_lnx_nfs_unstable",
    },
    "bounce": {
        "name": "mem_lnx_bounce",
    },
    "writeback_tmp": {
        "name": "mem_lnx_writeback_tmp",
    },
    "total_total": {
        "name": "mem_lnx_total_total",
    },
    "committed_as": {
        "name": "mem_lnx_committed_as",
    },
    "commit_limit": {
        "name": "mem_lnx_commit_limit",
    },
    "shmem": {
        "name": "mem_lnx_shmem",
    },
    "kernel_stack": {
        "name": "mem_lnx_kernel_stack",
    },
    "page_tables": {
        "name": "mem_lnx_page_tables",
    },
    "mlocked": {
        "name": "mem_lnx_mlocked",
    },
    "huge_pages_total": {
        "name": "mem_lnx_huge_pages_total",
    },
    "huge_pages_free": {
        "name": "mem_lnx_huge_pages_free",
    },
    "huge_pages_rsvd": {
        "name": "mem_lnx_huge_pages_rsvd",
    },
    "huge_pages_surp": {
        "name": "mem_lnx_huge_pages_surp",
    },
    "vmalloc_total": {
        "name": "mem_lnx_vmalloc_total",
    },
    "vmalloc_used": {
        "name": "mem_lnx_vmalloc_used",
    },
    "vmalloc_chunk": {
        "name": "mem_lnx_vmalloc_chunk",
    },
    "hardware_corrupted": {
        "name": "mem_lnx_hardware_corrupted",
    },
    # Several computed values should not be graphed because they
    # are already contained in the other graphs. Or because they
    # are bizarre
    "caches": {"name": "caches", "auto_graph": False},
    "swap_free": {"name": "swap_free", "auto_graph": False},
    "mem_free": {"name": "mem_free", "auto_graph": False},
    "sreclaimable": {"name": "mem_lnx_sreclaimable", "auto_graph": False},
    "pending": {"name": "mem_lnx_pending", "auto_graph": False},
    "sunreclaim": {"name": "mem_lnx_sunreclaim", "auto_graph": False},
    "anon_huge_pages": {"name": "mem_lnx_anon_huge_pages", "auto_graph": False},
    "anon_pages": {"name": "mem_lnx_anon_pages", "auto_graph": False},
    "mapped": {"name": "mem_lnx_mapped", "auto_graph": False},
    "active": {"name": "mem_lnx_active", "auto_graph": False},
    "inactive": {"name": "mem_lnx_inactive", "auto_graph": False},
    "total_used": {"name": "mem_lnx_total_used", "auto_graph": False},
    "unevictable": {"name": "mem_lnx_unevictable", "auto_graph": False},
    "cma_free": {"auto_graph": False},
    "cma_total": {"auto_graph": False},
}
check_metrics["check_mk-mem_vmalloc"] = {
    "used": {"name": "mem_lnx_vmalloc_used"},
    "chunk": {"name": "mem_lnx_vmalloc_chunk"},
}
tcp_conn_stats_translation: Dict[str, CheckMetricEntry] = {
    "SYN_SENT": {"name": "tcp_syn_sent"},
    "SYN_RECV": {"name": "tcp_syn_recv"},
    "ESTABLISHED": {"name": "tcp_established"},
    "LISTEN": {"name": "tcp_listen"},
    "TIME_WAIT": {"name": "tcp_time_wait"},
    "LAST_ACK": {"name": "tcp_last_ack"},
    "CLOSE_WAIT": {"name": "tcp_close_wait"},
    "CLOSED": {"name": "tcp_closed"},
    "CLOSING": {"name": "tcp_closing"},
    "FIN_WAIT1": {"name": "tcp_fin_wait1"},
    "FIN_WAIT2": {"name": "tcp_fin_wait2"},
    "BOUND": {"name": "tcp_bound"},
    "IDLE": {"name": "tcp_idle"},
}
check_metrics["check_mk-tcp_conn_stats"] = tcp_conn_stats_translation
check_metrics["check_mk-datapower_tcp"] = tcp_conn_stats_translation
check_metrics["check_mk_active-disk_smb"] = {
    "~.*": {"name": "fs_used"},
}
df_basic_perfvarnames = [
    "inodes_used",
    "fs_size",
    "growth",
    "trend",
    "reserved",
    "fs_free",
    "fs_provisioning",
    "uncommitted",
    "overprovisioned",
    "dedup_rate",
    "file_count",
]
df_translation: Dict[str, CheckMetricEntry] = {
    "~(?!%s).*$"
    % "|".join(df_basic_perfvarnames): {"name": "fs_used", "scale": MB, "deprecated": "2.0.0i1"},
    "fs_used": {"scale": MB},
    "fs_used_percent": {
        "auto_graph": False,
    },
    "fs_size": {"scale": MB},
    "reserved": {"scale": MB},
    "fs_free": {"scale": MB},
    "growth": {"name": "fs_growth", "scale": MB / 86400.0},
    "trend": {"name": "fs_trend", "scale": MB / 86400.0},
    "trend_hoursleft": {
        "scale": 3600,
    },
    "uncommitted": {
        "scale": MB,
    },
    "overprovisioned": {
        "scale": MB,
    },
}
check_metrics["check_mk-df"] = df_translation
check_metrics["check_mk-db2_logsizes"] = df_translation
check_metrics["check_mk-esx_vsphere_datastores"] = df_translation
check_metrics["check_mk-netapp_api_aggr"] = df_translation
check_metrics["check_mk-vms_df"] = df_translation
check_metrics["check_mk-vms_diskstat_df"] = df_translation
check_metrics["check_disk"] = df_translation
check_metrics["check_mk-df_netapp"] = df_translation
check_metrics["check_mk-df_netapp32"] = df_translation
check_metrics["check_mk-zfsget"] = df_translation
check_metrics["check_mk-hr_fs"] = df_translation
check_metrics["check_mk-oracle_asm_diskgroup"] = df_translation
check_metrics["check_mk-esx_vsphere_counters_ramdisk"] = df_translation
check_metrics["check_mk-hitachi_hnas_span"] = df_translation
check_metrics["check_mk-hitachi_hnas_volume"] = df_translation
check_metrics["check_mk-hitachi_hnas_volume_virtual"] = df_translation
check_metrics["check_mk-emcvnx_raidgroups_capacity"] = df_translation
check_metrics["check_mk-emcvnx_raidgroups_capacity_contiguous"] = df_translation
check_metrics["check_mk-ibm_svc_mdiskgrp"] = df_translation
check_metrics["check_mk-fast_lta_silent_cubes_capacity"] = df_translation
check_metrics["check_mk-fast_lta_volumes"] = df_translation
check_metrics["check_mk-libelle_business_shadow_archive_dir"] = df_translation
check_metrics["check_mk-netapp_api_luns"] = df_translation
check_metrics["check_mk-netapp_api_qtree_quota"] = df_translation
check_metrics["check_mk-emc_datadomain_fs"] = df_translation
check_metrics["check_mk-emc_isilon_quota"] = df_translation
check_metrics["check_mk-emc_isilon_ifs"] = df_translation
check_metrics["check_mk-3par_cpgs_usage"] = df_translation
check_metrics["check_mk-3par_capacity"] = df_translation
check_metrics["check_mk-3par_volumes"] = df_translation
check_metrics["check_mk-storeonce_clusterinfo_space"] = df_translation
check_metrics["check_mk-storeonce_servicesets_capacity"] = df_translation
check_metrics["check_mk-storeonce4x_appliances_storage"] = df_translation
check_metrics["check_mk-storeonce4x_cat_stores"] = df_translation
check_metrics["check_mk-numble_volumes"] = df_translation
check_metrics["check_mk-zpool"] = df_translation
check_metrics["check_mk-vnx_quotas"] = df_translation
###########################################################################
# NOTE: k8s_stats_fs is deprecated and will be
#       removed in Checkmk version 2.2.
###########################################################################
check_metrics["check_mk-k8s_stats_fs"] = df_translation
check_metrics["check_mk-sap_hana_diskusage"] = df_translation
check_metrics["check_mk-fjdarye200_pools"] = df_translation
check_metrics["check_mk-dell_compellent_folder"] = df_translation
check_metrics["check_mk-nimble_volumes"] = df_translation
check_metrics["check_mk-ceph_df"] = df_translation
check_metrics["check_mk-lvm_vgs"] = df_translation

check_metrics["check_mk-netapp_api_volumes"] = {
    "fs_used": {"scale": MB},
    "fs_used_percent": {
        "auto_graph": False,
    },
    "fs_size": {"scale": MB},
    "growth": {"name": "fs_growth", "scale": MB / 86400.0},
    "trend": {"name": "fs_trend", "scale": MB / 86400.0},
    "read_latency": {"scale": m},
    "write_latency": {"scale": m},
    "other_latency": {"scale": m},
    "nfs_read_latency": {"scale": m},
    "nfs_write_latency": {"scale": m},
    "nfs_other_latency": {"scale": m},
    "cifs_read_latency": {"scale": m},
    "cifs_write_latency": {"scale": m},
    "cifs_other_latency": {"scale": m},
    "san_read_latency": {"scale": m},
    "san_write_latency": {"scale": m},
    "san_other_latency": {"scale": m},
    "fcp_read_latency": {"scale": m},
    "fcp_write_latency": {"scale": m},
    "fcp_other_latency": {"scale": m},
    "iscsi_read_latency": {"scale": m},
    "iscsi_write_latency": {"scale": m},
    "iscsi_other_latency": {"scale": m},
}
disk_utilization_translation: Dict[str, CheckMetricEntry] = {
    "disk_utilization": {"scale": 100.0},
}
check_metrics["check_mk-diskstat"] = disk_utilization_translation
check_metrics["check_mk-emc_vplex_director_stats"] = disk_utilization_translation
check_metrics["check_mk-emc_vplex_volumes"] = disk_utilization_translation
check_metrics["check_mk-esx_vsphere_counters_diskio"] = disk_utilization_translation
check_metrics["check_mk-hp_msa_controller_io"] = disk_utilization_translation
check_metrics["check_mk-hp_msa_disk_io"] = disk_utilization_translation
check_metrics["check_mk-hp_msa_volume_io"] = disk_utilization_translation
check_metrics["check_mk-winperf_phydisk"] = disk_utilization_translation
check_metrics["check_mk-arbor_peakflow_sp_disk_usage"] = disk_utilization_translation
check_metrics["check_mk-arbor_peakflow_tms_disk_usage"] = disk_utilization_translation
check_metrics["check_mk-arbor_pravail_disk_usage"] = disk_utilization_translation
# in=0;;;0; inucast=0;;;; innucast=0;;;; indisc=0;;;; inerr=0;0.01;0.1;; out=0;;;0; outucast=0;;;; outnucast=0;;;; outdisc=0;;;; outerr=0;0.01;0.1;; outqlen=0;;;0;
if_translation: Dict[str, CheckMetricEntry] = {
    "in": {"name": "if_in_bps", "scale": 8},
    "out": {"name": "if_out_bps", "scale": 8},
    "total": {"name": "if_total_bps", "scale": 8},
    "indisc": {"name": "if_in_discards"},
    "inerr": {"name": "if_in_errors"},
    "outdisc": {"name": "if_out_discards"},
    "outerr": {"name": "if_out_errors"},
    "inmcast": {"name": "if_in_mcast"},
    "inbcast": {"name": "if_in_bcast"},
    "outmcast": {"name": "if_out_mcast"},
    "outbcast": {"name": "if_out_bcast"},
    "inucast": {"name": "if_in_unicast"},
    "innucast": {"name": "if_in_non_unicast"},
    "outucast": {"name": "if_out_unicast"},
    "outnucast": {"name": "if_out_non_unicast"},
}
check_metrics["check_mk-interfaces"] = if_translation
check_metrics["check_mk-aws_ec2_network_io"] = if_translation
check_metrics["check_mk-aws_rds_network_io"] = if_translation
check_metrics["check_mk-cadvisor_if"] = if_translation
check_metrics["check_mk-esx_vsphere_counters_if"] = if_translation
check_metrics["check_mk-esx_vsphere_counters"] = if_translation
check_metrics["check_mk-fritz"] = if_translation
check_metrics["check_mk-fritz_wan_if"] = if_translation
check_metrics["check_mk-hitachi_hnas_fc_if"] = if_translation
check_metrics["check_mk-hpux_if"] = if_translation
check_metrics["check_mk-huawei_osn_if"] = if_translation
check_metrics["check_mk-if64"] = if_translation
###########################################################################
# NOTE: k8s_stats_network is deprecated and will be
#       removed in Checkmk version 2.2.
###########################################################################
check_metrics["check_mk-k8s_stats_network"] = if_translation
check_metrics["check_mk-lnx_if"] = if_translation
check_metrics["check_mk-mcdata_fcport"] = if_translation
check_metrics["check_mk-netapp_api_if"] = if_translation
check_metrics["check_mk-winperf_if"] = if_translation
check_metrics["check_mk-brocade_fcport"] = {
    "in": {
        "name": "fc_rx_bytes",
    },
    "out": {
        "name": "fc_tx_bytes",
    },
    "rxframes": {
        "name": "fc_rx_frames",
    },
    "txframes": {
        "name": "fc_tx_frames",
    },
    "rxcrcs": {"name": "fc_crc_errors"},
    "rxencoutframes": {"name": "fc_encouts"},
    "rxencinframes": {"name": "fc_encins"},
    "c3discards": {"name": "fc_c3discards"},
    "notxcredits": {"name": "fc_notxcredits"},
}
check_metrics["check_mk-fc_port"] = {
    "in": {
        "name": "fc_rx_bytes",
    },
    "out": {
        "name": "fc_tx_bytes",
    },
    "rxobjects": {
        "name": "fc_rx_frames",
    },
    "txobjects": {
        "name": "fc_tx_frames",
    },
    "rxcrcs": {"name": "fc_crc_errors"},
    "rxencoutframes": {"name": "fc_encouts"},
    "c3discards": {"name": "fc_c3discards"},
    "notxcredits": {"name": "fc_notxcredits"},
}
check_metrics["check_mk-qlogic_fcport"] = {
    "in": {
        "name": "fc_rx_bytes",
    },
    "out": {
        "name": "fc_tx_bytes",
    },
    "rxframes": {
        "name": "fc_rx_frames",
    },
    "txframes": {
        "name": "fc_tx_frames",
    },
    "link_failures": {"name": "fc_link_fails"},
    "sync_losses": {"name": "fc_sync_losses"},
    "prim_seq_proto_errors": {"name": "fc_prim_seq_errors"},
    "invalid_tx_words": {"name": "fc_invalid_tx_words"},
    "discards": {"name": "fc_c2c3_discards"},
    "invalid_crcs": {"name": "fc_invalid_crcs"},
    "address_id_errors": {"name": "fc_address_id_errors"},
    "link_reset_ins": {"name": "fc_link_resets_in"},
    "link_reset_outs": {"name": "fc_link_resets_out"},
    "ols_ins": {"name": "fc_offline_seqs_in"},
    "ols_outs": {"name": "fc_offline_seqs_out"},
    "c2_fbsy_frames": {"name": "fc_c2_fbsy_frames"},
    "c2_frjt_frames": {"name": "fc_c2_frjt_frames"},
}
check_metrics["check_mk-mysql_innodb_io"] = {
    "read": {"name": "disk_read_throughput"},
    "write": {"name": "disk_write_throughput"},
}
check_metrics["check_mk-esx_vsphere_counters_diskio"] = {
    "read": {"name": "disk_read_throughput"},
    "write": {"name": "disk_write_throughput"},
    "ios": {"name": "disk_ios"},
    "latency": {"name": "disk_latency"},
    "disk_utilization": {"scale": 100.0},
}
check_metrics["check_mk-emcvnx_disks"] = {
    "read": {"name": "disk_read_throughput"},
    "write": {"name": "disk_write_throughput"},
}
check_metrics["check_mk-diskstat"] = {
    "read": {"name": "disk_read_throughput"},
    "write": {"name": "disk_write_throughput"},
    "disk_utilization": {"scale": 100.0},
}
check_metrics["check_mk-aix_diskiod"] = {
    "read": {"name": "disk_read_throughput"},
    "write": {"name": "disk_write_throughput"},
    "disk_utilization": {"scale": 100.0},
}
check_metrics["check_mk-ibm_svc_systemstats_iops"] = {
    "read": {"name": "disk_read_ios"},
    "write": {"name": "disk_write_ios"},
}
check_metrics["check_mk-docker_node_info_containers"] = {
    "containers": {"name": "docker_all_containers"},
    "running": {"name": "docker_running_containers"},
    "paused": {"name": "docker_paused_containers"},
    "stopped": {"name": "docker_stopped_containers"},
}
check_metrics["check_mk-docker_node_disk_usage"] = {
    "count": {"name": "docker_count"},
    "active": {"name": "docker_active"},
    "size": {"name": "docker_size"},
    "reclaimable": {"name": "docker_reclaimable"},
}
check_metrics["check_mk-dell_powerconnect_temp"] = {
    "temperature": {"name": "temp"},
}
check_metrics["check_mk-bluecoat_diskcpu"] = {
    "value": {"name": "generic_util"},
}
check_metrics["check_mk-mgmt_ipmi_sensors"] = {
    "value": {"name": "temp"},
}
check_metrics["check_mk-ipmi_sensors"] = {
    "value": {"name": "temp"},
}
check_metrics["check_mk-ipmi"] = {
    "ambient_temp": {"name": "temp"},
}
check_metrics["check_mk-wagner_titanus_topsense_airflow_deviation"] = {
    "airflow_deviation": {"name": "deviation_airflow"}
}
check_metrics["check_mk-wagner_titanus_topsense_chamber_deviation"] = {
    "chamber_deviation": {"name": "deviation_calibration_point"}
}
check_metrics["check_mk-apc_symmetra"] = {
    "OutputLoad": {"name": "output_load"},
    "batcurr": {"name": "battery_current"},
    "systemp": {"name": "battery_temp"},
    "capacity": {"name": "battery_capacity"},
    "runtime": {"name": "lifetime_remaining", "scale": 60},
}
check_metrics["check_mk-apc_symmetra_temp"] = {
    "systemp": {"name": "battery_temp"},
}
check_metrics["check_mk-apc_symmetra_elphase"] = {
    "OutputLoad": {"name": "output_load"},
    "batcurr": {"name": "battery_current"},
}
cpu_util_unix_translate: Dict[str, CheckMetricEntry] = {
    "wait": {"name": "io_wait"},
    "guest": {"name": "cpu_util_guest"},
    "steal": {"name": "cpu_util_steal"},
}
check_metrics["check_mk-kernel_util"] = cpu_util_unix_translate
check_metrics["check_mk-statgrab_cpu"] = cpu_util_unix_translate
check_metrics["check_mk-lxc_container_cpu"] = cpu_util_unix_translate
check_metrics["check_mk-emc_ecs_cpu_util"] = cpu_util_unix_translate
check_metrics["check_mk-lparstat_aix_cpu_util"] = {
    "wait": {"name": "io_wait"},
}
check_metrics["check_mk-ucd_cpu_util"] = {
    "wait": {"name": "io_wait"},
}
check_metrics["check_mk-vms_cpu"] = {
    "wait": {"name": "io_wait"},
}
check_metrics["check_mk-vms_sys_util"] = {
    "wait": {"name": "io_wait"},
}
check_metrics["check_mk-winperf_cpuusage"] = {
    "cpuusage": {"name": "util"},
}
check_metrics["check_mk-h3c_lanswitch_cpu"] = {
    "usage": {"name": "util"},
}
check_metrics["check_mk-brocade_mlx_module_cpu"] = {
    "cpu_util1": {"name": "util1s"},
    "cpu_util5": {"name": "util5s"},
    "cpu_util60": {"name": "util1"},
    "cpu_util200": {"name": "util5"},
}
check_metrics["check_mk-dell_powerconnect_cpu"] = {
    "load": {"name": "util", "deprecated": "2.0.0p4"},
    "loadavg 60s": {"name": "util1", "deprecated": "2.0.0p4"},
    "loadavg 5m": {"name": "util5", "deprecated": "2.0.0p4"},
}
check_metrics["check_mk-ibm_svc_nodestats_cache"] = {
    "write_cache_pc": {"name": "write_cache_usage"},
    "total_cache_pc": {"name": "total_cache_usage"},
}
check_metrics["check_mk-ibm_svc_systemstats_cache"] = {
    "write_cache_pc": {"name": "write_cache_usage"},
    "total_cache_pc": {"name": "total_cache_usage"},
}
mem_vsphere_hostsystem: Dict[str, CheckMetricEntry] = {
    "usage": {"name": "mem_used", "deprecated": "2.0.0i1"},
    "mem_total": {"auto_graph": False},
}
check_metrics["check_mk-esx_vsphere_hostsystem_mem_usage"] = mem_vsphere_hostsystem
check_metrics["check_mk-esx_vsphere_hostsystem_mem_usage_cluster"] = mem_vsphere_hostsystem
check_metrics["check_mk-ibm_svc_host"] = {
    "active": {"name": "hosts_active"},
    "inactive": {"name": "hosts_inactive"},
    "degraded": {"name": "hosts_degraded"},
    "offline": {"name": "hosts_offline"},
    "other": {"name": "hosts_other"},
}
juniper_mem: Dict[str, CheckMetricEntry] = {
    "usage": {"name": "mem_used", "deprecated": "2.0.0i1"},
}
check_metrics["check_mk-juniper_screenos_mem"] = juniper_mem
check_metrics["check_mk-juniper_trpz_mem"] = juniper_mem
check_metrics["check_mk-ibm_svc_nodestats_iops"] = {
    "read": {"name": "disk_read_ios"},
    "write": {"name": "disk_write_ios"},
}
check_metrics["check_mk-openvpn_clients"] = {
    "in": {"name": "if_in_octets"},
    "out": {"name": "if_out_octets"},
}
check_metrics["check_mk-f5_bigip_interfaces"] = {
    "bytes_in": {"name": "if_in_octets"},
    "bytes_out": {"name": "if_out_octets"},
}
check_metrics["check_mk-f5_bigip_conns"] = {
    "conns": {"name": "connections"},
    "ssl_conns": {"name": "connections_ssl"},
}
check_metrics["check_mk-f5_bigip_mem"] = memory_simple_translation
check_metrics["check_mk-f5_bigip_mem_tmm"] = memory_simple_translation
check_metrics["check_mk-mbg_lantime_state"] = {
    "offset": {"name": "time_offset", "scale": 0.000001}
}  # convert us -> sec
check_metrics["check_mk-mbg_lantime_ng_state"] = {
    "offset": {"name": "time_offset", "scale": 0.000001}
}  # convert us -> sec
check_metrics["check_mk-systemtime"] = {
    "offset": {"name": "time_offset"},
}
check_metrics["check_mk-ntp"] = {
    "offset": {"name": "time_offset", "scale": m},
    "jitter": {"scale": m},
}
check_metrics["check_mk-chrony"] = {
    "offset": {"name": "time_offset", "scale": m},
}
check_metrics["check_mk-ntp_time"] = {
    "offset": {"name": "time_offset", "scale": m},
    "jitter": {"scale": m},
}
check_metrics["check_mk-adva_fsp_if"] = {
    "output_power": {"name": "output_signal_power_dbm"},
    "input_power": {"name": "input_signal_power_dbm"},
}
check_metrics["check_mk-allnet_ip_sensoric_tension"] = {
    "tension": {"name": "voltage_percent"},
}
check_metrics["check_mk-apache_status"] = {
    "Uptime": {"name": "uptime"},
    "IdleWorkers": {"name": "idle_workers"},
    "BusyWorkers": {"name": "busy_workers"},
    "IdleServers": {"name": "idle_servers"},
    "BusyServers": {"name": "busy_servers"},
    "OpenSlots": {"name": "open_slots"},
    "TotalSlots": {"name": "total_slots"},
    "CPULoad": {"name": "load1"},
    "ReqPerSec": {"name": "requests_per_second"},
    "BytesPerSec": {"name": "direkt_io"},
    "ConnsTotal": {"name": "connections"},
    "ConnsAsyncWriting": {"name": "connections_async_writing"},
    "ConnsAsyncKeepAlive": {"name": "connections_async_keepalive"},
    "ConnsAsyncClosing": {"name": "connections_async_closing"},
    "State_StartingUp": {"name": "apache_state_startingup"},
    "State_Waiting": {"name": "apache_state_waiting"},
    "State_Logging": {"name": "apache_state_logging"},
    "State_DNS": {"name": "apache_state_dns"},
    "State_SendingReply": {"name": "apache_state_sending_reply"},
    "State_ReadingRequest": {"name": "apache_state_reading_request"},
    "State_Closing": {"name": "apache_state_closing"},
    "State_IdleCleanup": {"name": "apache_state_idle_cleanup"},
    "State_Finishing": {"name": "apache_state_finishing"},
    "State_Keepalive": {"name": "apache_state_keep_alive"},
}
check_metrics["check_mk-ups_socomec_out_voltage"] = {
    "out_voltage": {"name": "voltage"},
}
check_metrics["check_mk-hp_blade_psu"] = {
    "output": {"name": "power"},
}
check_metrics["check_mk-apc_rackpdu_power"] = {
    "amperage": {"name": "current"},
}
check_metrics["check_mk-apc_ats_output"] = {
    "volt": {"name": "voltage"},
    "watt": {"name": "power"},
    "ampere": {"name": "current"},
    "load_perc": {"name": "output_load"},
}
check_metrics["check_mk-ups_out_load"] = {
    "out_load": {"name": "output_load"},
    "out_voltage": {"name": "voltage"},
}
check_metrics["check_mk-raritan_pdu_outletcount"] = {
    "outletcount": {"name": "connector_outlets"},
}
check_metrics["check_mk-docsis_channels_upstream"] = {
    "total": {"name": "total_modems"},
    "active": {"name": "active_modems"},
    "registered": {"name": "registered_modems"},
    "util": {"name": "channel_utilization"},
    "frequency": {"scale": 1000000.0},
    "codewords_corrected": {"scale": 100.0},
    "codewords_uncorrectable": {"scale": 100.0},
}
check_metrics["check_mk-docsis_channels_downstream"] = {
    "power": {"name": "downstream_power"},
}
check_metrics["check_mk-zfs_arc_cache"] = {
    "hit_ratio": {
        "name": "cache_hit_ratio",
    },
    "size": {
        "name": "caches",
    },
    "arc_meta_used": {
        "name": "zfs_metadata_used",
    },
    "arc_meta_limit": {
        "name": "zfs_metadata_limit",
    },
    "arc_meta_max": {
        "name": "zfs_metadata_max",
    },
}
check_metrics["check_mk-zfs_arc_cache_l2"] = {
    "l2_size": {"name": "zfs_l2_size"},
    "l2_hit_ratio": {
        "name": "zfs_l2_hit_ratio",
    },
}
check_metrics["check_mk-postgres_sessions"] = {
    "total": {"name": "total_sessions"},
    "running": {"name": "running_sessions"},
}
check_metrics["check_mk-fileinfo"] = {
    "size": {"name": "file_size"},
}
check_metrics["check_mk-fileinfo_groups"] = {
    "size": {"name": "total_file_size"},
    "size_smallest": {"name": "file_size_smallest"},
    "size_largest": {"name": "file_size_largest"},
    "count": {"name": "file_count"},
    "age_oldest": {"name": "file_age_oldest"},
    "age_newest": {"name": "file_age_newest"},
}
check_metrics["check_mk-postgres_stat_database_size"] = {
    "size": {"name": "database_size"},
}
check_metrics["check_mk-oracle_sessions"] = {
    "sessions": {"name": "running_sessions"},
}
check_metrics["check_mk-oracle_logswitches"] = {
    "logswitches": {"name": "logswitches_last_hour"},
}
check_metrics["check_mk-oracle_dataguard_stats"] = {
    "apply_lag": {"name": "database_apply_lag"},
}
check_metrics["check_mk-oracle_performance"] = {
    "DB_CPU": {"name": "oracle_db_cpu"},
    "DB_time": {"name": "oracle_db_time"},
    "buffer_hit_ratio": {"name": "oracle_buffer_hit_ratio"},
    "db_block_gets": {"name": "oracle_db_block_gets"},
    "db_block_change": {"name": "oracle_db_block_change"},
    "consistent_gets": {"name": "oracle_db_block_gets"},
    "physical_reads": {"name": "oracle_physical_reads"},
    "physical_writes": {"name": "oracle_physical_writes"},
    "free_buffer_wait": {"name": "oracle_free_buffer_wait"},
    "buffer_busy_wait": {"name": "oracle_buffer_busy_wait"},
    "library_cache_hit_ratio": {"name": "oracle_library_cache_hit_ratio"},
    "pinssum": {"name": "oracle_pins_sum"},
    "pinhitssum": {"name": "oracle_pin_hits_sum"},
}
check_metrics["check_mk-db2_logsize"] = {
    "~[_/]": {"name": "fs_used", "scale": MB, "deprecated": "2.0.0i1"},
    "fs_used": {"scale": MB},
    "fs_used_percent": {
        "auto_graph": False,
    },
}
check_metrics["check_mk-steelhead_connections"] = {
    "active": {"name": "fw_connections_active"},
    "established": {"name": "fw_connections_established"},
    "halfOpened": {"name": "fw_connections_halfopened"},
    "halfClosed": {"name": "fw_connections_halfclosed"},
    "passthrough": {"name": "fw_connections_passthrough"},
}
check_metrics["check_mk-oracle_tablespaces"] = {
    "size": {"name": "tablespace_size"},
    "used": {"name": "tablespace_used"},
    "max_size": {"name": "tablespace_max_size"},
}
check_metrics["check_mk-mssql_tablespaces"] = {
    "size": {"name": "database_size"},
    "unallocated": {"name": "unallocated_size"},
    "reserved": {"name": "reserved_size"},
    "data": {"name": "data_size"},
    "indexes": {"name": "indexes_size"},
    "unused": {"name": "unused_size"},
}
check_metrics["check_mk-f5_bigip_vserver"] = {
    "conn_rate": {"name": "connections_rate"},
}
check_metrics["check_mk-arcserve_backup"] = {
    "size": {
        "name": "backup_size",
    },
    "dirs": {
        "name": "directories",
    },
    "files": {
        "name": "file_count",
    },
}
check_metrics["check_mk-oracle_longactivesessions"] = {
    "count": {
        "name": "oracle_count",
    },
}
check_metrics["check_mk-oracle_rman"] = {
    "age": {"name": "backup_age"},
}
check_metrics["check_mk-veeam_client"] = {
    "totalsize": {"name": "backup_size"},
    "duration": {"name": "backup_duration"},
    "avgspeed": {"name": "backup_avgspeed"},
}
check_metrics["check_mk-cups_queues"] = {
    "jobs": {"name": "printer_queue"},
}
mq_translation: Dict[str, CheckMetricEntry] = {
    "queue": {"name": "messages_in_queue"},
}
check_metrics["check_mk-mq_queues"] = mq_translation
check_metrics["check_mk-websphere_mq_channels"] = mq_translation
check_metrics["check_mk-websphere_mq_queues"] = mq_translation
check_metrics["check_mk-printer_pages"] = {
    "pages": {"name": "pages_total"},
}
check_metrics["check_mk-livestatus_status"] = {
    "host_checks": {"name": "host_check_rate"},
    "service_checks": {"name": "service_check_rate"},
    "connections": {"name": "livestatus_connect_rate"},
    "requests": {"name": "livestatus_request_rate"},
    "log_messages": {"name": "log_message_rate"},
}
check_metrics["check_mk-cisco_wlc_clients"] = {
    "clients": {"name": "connections"},
}
check_metrics["check_mk-cisco_qos"] = {
    "drop": {"name": "qos_dropped_bytes_rate"},
    "post": {"name": "qos_outbound_bytes_rate"},
}
check_metrics["check_mk-hivemanager_devices"] = {
    "clients_count": {"name": "connections"},
}
check_metrics["check_mk-ibm_svc_license"] = {
    "licensed": {"name": "licenses"},
}
check_metrics["check_mk-tsm_stagingpools"] = {
    "free": {"name": "tapes_free"},
    "tapes": {"name": "tapes_total"},
    "util": {"name": "tapes_util"},
}
check_metrics["check_mk-tsm_storagepools"] = {
    "used": {"name": "used_space"},
}
check_metrics["check_mk-hpux_tunables_shmseg"] = {
    "segments": {"name": "shared_memory_segments"},
}
check_metrics["check_mk-hpux_tunables_semmns"] = {
    "entries": {"name": "semaphores"},
}
check_metrics["check_mk-hpux_tunables_maxfiles_lim"] = {
    "files": {"name": "files_open"},
}
check_metrics["check_mk-win_dhcp_pools"] = {
    "free": {"name": "free_dhcp_leases"},
    "used": {"name": "used_dhcp_leases"},
    "pending": {"name": "pending_dhcp_leases"},
}
check_metrics["check_mk-lparstat_aix"] = {
    "sys": {"name": "system"},
    "wait": {"name": "io_wait"},
}
check_metrics["check_mk-netapp_fcpio"] = {
    "read": {"name": "disk_read_throughput"},
    "write": {"name": "disk_write_throughput"},
}
check_metrics["check_mk-netapp_api_vf_stats_traffic"] = {
    "read_bytes": {"name": "disk_read_throughput"},
    "write_bytes": {"name": "disk_write_throughput"},
    "read_ops": {"name": "disk_read_ios"},
    "write_ops": {"name": "disk_write_ios"},
}
check_metrics["check_mk-job"] = {
    "reads": {"name": "disk_read_throughput"},
    "writes": {"name": "disk_write_throughput"},
    "real_time": {"name": "job_duration"},
}
ps_translation: Dict[str, CheckMetricEntry] = {
    "count": {"name": "processes"},
    "vsz": {
        "name": "process_virtual_size",
        "scale": KB,
    },
    "rss": {
        "name": "process_resident_size",
        "scale": KB,
    },
    "pcpu": {"name": "util"},
    "pcpuavg": {"name": "util_average"},
}
check_metrics["check_mk-smart_stats"] = {
    "Power_On_Hours": {"name": "uptime", "scale": 3600},
    "Power_Cycle_Count": {"name": "harddrive_power_cycles"},
    "Reallocated_Sector_Ct": {"name": "harddrive_reallocated_sectors"},
    "Reallocated_Event_Count": {"name": "harddrive_reallocated_events"},
    "Spin_Retry_Count": {"name": "harddrive_spin_retries"},
    "Current_Pending_Sector": {"name": "harddrive_pending_sectors"},
    "Command_Timeout": {"name": "harddrive_cmd_timeouts"},
    "End-to-End_Error": {"name": "harddrive_end_to_end_errors"},
    "Reported_Uncorrect": {"name": "harddrive_uncorrectable_errors"},
    "UDMA_CRC_Error_Count": {"name": "harddrive_udma_crc_errors"},
    "CRC_Error_Count": {
        "name": "harddrive_crc_errors",
    },
    "Uncorrectable_Error_Cnt": {
        "name": "harddrive_uncorrectable_errors",
    },
    "Power_Cycles": {"name": "harddrive_power_cycles"},
    "Media_and_Data_Integrity_Errors": {"name": "nvme_media_and_data_integrity_errors"},
    "Error_Information_Log_Entries": {"name": "nvme_error_information_log_entries"},
    "Critical_Warning": {"name": "nvme_critical_warning"},
    "Available_Spare": {"name": "nvme_available_spare"},
    "Percentage_Used": {"name": "nvme_spare_percentage_used"},
    "Data_Units_Read": {"name": "nvme_data_units_read"},
    "Data_Units_Written": {"name": "nvme_data_units_written"},
}
check_metrics["check_mk-ps"] = ps_translation
check_metrics["check_mk-mssql_counters_sqlstats"] = {
    "batch_requests/sec": {"name": "requests_per_second"},
    "sql_compilations/sec": {"name": "requests_per_second"},
    "sql_re-compilations/sec": {"name": "requests_per_second"},
}
check_metrics["check_mk-mssql_counters_file_sizes"] = {
    "log_files": {"name": "log_files_total"},
}
check_metrics["check_mk-mssql_counters_locks"] = {
    "lock_requests/sec": {"name": "lock_requests_per_second"},
    "lock_timeouts/sec": {"name": "lock_timeouts_per_second"},
    "number_of_deadlocks/sec": {"name": "number_of_deadlocks_per_second"},
    "lock_waits/sec": {"name": "lock_waits_per_second"},
}
check_metrics["check_mk-mssql_counters_pageactivity"] = {
    "page_reads/sec": {"name": "page_reads_per_second"},
    "page_writes/sec": {"name": "page_writes_per_second"},
    "page_lookups/sec": {"name": "page_lookups_per_second"},
}
check_metrics["check_mk-mssql_counters_transactions"] = {
    "transactions/sec": {"name": "transactions_per_second"},
    "write_transactions/sec": {"name": "write_transactions_per_second"},
    "tracked_transactions/sec": {"name": "tracked_transactions_per_second"},
}
cisco_mem_translation: Dict[str, CheckMetricEntry] = {
    "mem_used": {"name": "mem_used_percent", "deprecated": "2.0.0i1"},
}
check_metrics["check_mk-cisco_cpu_memory"] = cisco_mem_translation
check_metrics["check_mk-cisco_sys_mem"] = cisco_mem_translation
cisco_mem_translation_with_trend = dict(cisco_mem_translation)
cisco_mem_translation_with_trend.update(
    {
        "growth": {"name": "mem_growth"},
        "trend": {"name": "mem_trend"},
    }
)
check_metrics["check_mk-cisco_mem"] = cisco_mem_translation_with_trend
check_metrics["check_mk-cisco_mem_asa"] = cisco_mem_translation_with_trend
check_metrics["check_mk-cisco_mem_asa64"] = cisco_mem_translation_with_trend
check_metrics["check_mk-fortigate_sessions_base"] = {
    "session": {"name": "active_sessions"},
}
check_metrics["check_mk-cisco_asa_svcsessions"] = {
    "active": {"name": "active_sessions"},
}

for check_name in ["aws_elb_http_elb", "aws_elb_http_backend", "aws_elbv2_application_http_elb"]:
    check_metrics["check_mk-%s" % check_name] = {
        "http_4xx_rate": {"name": "aws_http_4xx_rate"},
        "http_5xx_rate": {"name": "aws_http_5xx_rate"},
        "http_4xx_perc": {"name": "aws_http_4xx_perc"},
        "http_5xx_perc": {"name": "aws_http_5xx_perc"},
    }
check_metrics["check_mk-aws_elb_backend_connection_errors"] = {
    "backend_connection_errors_rate": {"name": "aws_backend_connection_errors_rate"},
}
check_metrics["check_mk-aws_elbv2_application_connections"] = {
    "aws_Active_connections": {"name": "aws_active_connections"},
    "aws_New_connections": {"name": "aws_new_connections"},
    "aws_Rejected_connections": {"name": "aws_rejected_connections"},
    "aws_TLS errors_connections": {"name": "aws_client_tls_errors"},
}
check_metrics["check_mk-aws_s3_requests_http_errors"] = {
    "http_4xx_rate": {"name": "aws_http_4xx_rate"},
    "http_5xx_rate": {"name": "aws_http_5xx_rate"},
    "http_4xx_perc": {"name": "aws_http_4xx_perc"},
    "http_5xx_perc": {"name": "aws_http_5xx_perc"},
}
check_metrics["check_mk-ups_capacity"] = {
    "capacity": {
        "name": "battery_seconds_remaining",
        "deprecated": "2.0.0b2",
    },
    "percent": {
        "name": "battery_capacity",
        "deprecated": "2.0.0b2",
    },
}
