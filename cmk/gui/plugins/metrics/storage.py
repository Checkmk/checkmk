#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import graph_info, metric_info

# .
#   .--Metrics-------------------------------------------------------------.
#   |                   __  __      _        _                             |
#   |                  |  \/  | ___| |_ _ __(_) ___ ___                    |
#   |                  | |\/| |/ _ \ __| '__| |/ __/ __|                   |
#   |                  | |  | |  __/ |_| |  | | (__\__ \                   |
#   |                  |_|  |_|\___|\__|_|  |_|\___|___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Definitions of metrics                                              |
#   '----------------------------------------------------------------------'

# Title are always lower case - except the first character!
# Colors: See indexed_color() in cmk/gui/plugins/metrics/utils.py

metric_info["age"] = {
    "title": _("Age"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["last_updated"] = {
    "title": _("Last Updated"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["deferred_age"] = {
    "title": _("Deferred Files Age"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["runtime"] = {
    "title": _("Process Runtime"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["lifetime_remaining"] = {
    "title": _("Lifetime remaining"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["streams"] = {
    "title": _("Streams"),
    "unit": "%",
    "color": "35/a",
}

metric_info["cache_misses_rate"] = {
    "title": _("Cache misses per second"),
    "unit": "1/s",
    "color": "#ba60ba",
}

metric_info["cache_hit_ratio"] = {
    "title": _("Cache hit ratio"),
    "unit": "%",
    "color": "#60c0c0",
}

metric_info["zfs_l2_hit_ratio"] = {
    "title": _("L2 cache hit ratio"),
    "unit": "%",
    "color": "46/a",
}

metric_info["prefetch_data_hit_ratio"] = {
    "title": _("Prefetch data hit ratio"),
    "unit": "%",
    "color": "41/b",
}

metric_info["prefetch_metadata_hit_ratio"] = {
    "title": _("Prefetch metadata hit ratio"),
    "unit": "%",
    "color": "43/a",
}

metric_info["zfs_metadata_used"] = {
    "title": _("Used meta data"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["zfs_metadata_max"] = {
    "title": _("Maxmimum of meta data"),
    "unit": "bytes",
    "color": "33/a",
}

metric_info["zfs_metadata_limit"] = {
    "title": _("Limit of meta data"),
    "unit": "bytes",
    "color": "36/a",
}

metric_info["zfs_l2_size"] = {
    "title": _("L2 cache size"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["file_size"] = {
    "title": _("File size"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["total_file_size"] = {
    "title": _("Total file size"),
    "unit": "bytes",
    "color": "16/a",
}
metric_info["file_size_smallest"] = {
    "title": _("Smallest file"),
    "unit": "bytes",
    "color": "21/a",
}

metric_info["file_size_largest"] = {
    "title": _("Largest file"),
    "unit": "bytes",
    "color": "25/a",
}

metric_info["file_count"] = {
    "title": _("Amount of files"),
    "unit": "count",
    "color": "23/a",
}

metric_info["new_files"] = {
    "title": _("New files in Spool"),
    "unit": "count",
    "color": "23/a",
}

metric_info["deferred_files"] = {
    "title": _("Deferred files in Spool"),
    "unit": "count",
    "color": "16/a",
}

metric_info["corrupted_files"] = {
    "title": _("Corrupted files in Spool"),
    "unit": "count",
    "color": "34/a",
}

# cloud storage

metric_info["used_space"] = {
    "title": _("Used storage space"),
    "unit": "bytes",
    "color": "34/a",
}

metric_info["ingress"] = {
    "title": _("Data ingress"),
    "unit": "bytes",
    "color": "15/a",
}

metric_info["egress"] = {
    "title": _("Data engress"),
    "unit": "bytes",
    "color": "43/a",
}

metric_info["data_files"] = {
    "title": _("Data files size"),
    "unit": "bytes",
    "color": "34/a",
}

metric_info["log_files_used"] = {
    "title": _("Used size of log files"),
    "unit": "bytes",
    "color": "25/a",
}

metric_info["log_files_total"] = {
    "title": _("Total size of log files"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["database_size"] = {
    "title": _("Database size"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["data_size"] = {
    "title": _("Data size"),
    "unit": "bytes",
    "color": "25/a",
}

metric_info["size_on_disk"] = {
    "title": _("Size on disk"),
    "unit": "bytes",
    "color": "25/b",
}

metric_info["unallocated_size"] = {
    "title": _("Unallocated space"),
    "help": _("Space in the database that has not been reserved for database objects"),
    "unit": "bytes",
    "color": "34/a",
}

metric_info["reserved_size"] = {
    "title": _("Reserved space"),
    "help": _("Total amount of space allocated by objects in the database"),
    "unit": "bytes",
    "color": "41/a",
}

metric_info["indexes_size"] = {
    "title": _("Index space"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["unused_size"] = {
    "title": _("Unused space"),
    "help": _("Total amount of space reserved for objects in the database, but not yed used"),
    "unit": "bytes",
    "color": "46/a",
}

metric_info["allocated_size"] = {
    "title": _("Allocated space"),
    "unit": "bytes",
    "color": "42/a",
}

metric_info["tablespace_size"] = {
    "title": _("Tablespace size"),
    "unit": "bytes",
    "color": "#092507",
}

metric_info["tablespace_used"] = {
    "title": _("Tablespace used"),
    "unit": "bytes",
    "color": "#e59d12",
}

metric_info["tablespace_max_size"] = {
    "title": _("Tablespace maximum size"),
    "unit": "bytes",
    "color": "#172121",
}

metric_info["tablespace_wasted"] = {
    "title": _("Tablespace wasted"),
    "unit": "bytes",
    "color": "#a02020",
}

metric_info["indexspace_wasted"] = {
    "title": _("Indexspace wasted"),
    "unit": "bytes",
    "color": "#20a080",
}

metric_info["database_reclaimable"] = {
    "title": _("Database reclaimable size"),
    "unit": "bytes",
    "color": "45/a",
}

metric_info["mem_total"] = {
    "title": _("RAM installed"),
    "color": "#f0f0f0",
    "unit": "bytes",
}

metric_info["memory_avg"] = {
    "title": _("Memory Average"),
    "color": "#80ff40",
    "unit": "bytes",
}

metric_info["pagefile_avg"] = {
    "title": _("Commit Charge Average"),
    "color": "#408f20",
    "unit": "bytes",
}

metric_info["mem_free"] = {
    "title": _("Free RAM"),
    "color": "#ffffff",
    "unit": "bytes",
}

metric_info["mem_used"] = {
    "color": "#80ff40",
    "title": _("RAM used"),
    "unit": "bytes",
}

metric_info["mem_available"] = {
    "color": "21/a",
    "title": _("Estimated RAM for new processes"),
    "unit": "bytes",
}

metric_info["pagefile_used"] = {
    "color": "#408f20",
    "title": _("Commit Charge"),
    "unit": "bytes",
}

metric_info["mem_used_percent"] = {
    "color": "#80ff40",
    "title": _("RAM used %"),
    "unit": "%",
}

metric_info["cpu_mem_used_percent"] = {
    "color": "#80ff40",
    "title": _("CPU Memory used"),
    "unit": "%",
}

metric_info["mem_perm_used"] = {
    "color": "#80ff40",
    "title": _("Permanent Generation Memory"),
    "unit": "bytes",
}

metric_info["mem_growth"] = {
    "title": _("Memory usage growth"),
    "unit": "bytes/d",
    "color": "#29cfaa",
}

metric_info["mem_trend"] = {
    "title": _("Trend of memory usage growth"),
    "unit": "bytes/d",
    "color": "#808080",
}

metric_info["trend_hoursleft"] = {
    "title": _("Time left until full"),
    "unit": "s",
    "color": "#94b65a",
}

metric_info["swap_total"] = {
    "title": _("Swap installed"),
    "color": "#e0e0e0",
    "unit": "bytes",
}

metric_info["swap_free"] = {
    "title": _("Free swap space"),
    "unit": "bytes",
    "color": "#eeeeee",
}

metric_info["swap_used"] = {
    "title": _("Swap used"),
    "color": "#408f20",
    "unit": "bytes",
}

metric_info["swap_used_percent"] = {
    "color": "#408f20",
    "title": _("Swap used"),
    "unit": "%",
}

metric_info["swap_cached"] = {
    "title": _("Swap cached"),
    "color": "#5bebc9",
    "unit": "bytes",
}

metric_info["caches"] = {
    "title": _("Memory used by caches"),
    "unit": "bytes",
    "color": "51/a",
}

metric_info["mem_pages_rate"] = {
    "title": _("Memory Pages"),
    "unit": "1/s",
    "color": "34/a",
}

metric_info["mem_lnx_total_used"] = {
    "title": _("Total used memory"),
    "color": "#70f038",
    "unit": "bytes",
}

metric_info["mem_lnx_cached"] = {
    "title": _("Cached memory"),
    "color": "#91cceb",
    "unit": "bytes",
}

metric_info["mem_lnx_buffers"] = {
    "title": _("Buffered memory"),
    "color": "#5bb9eb",
    "unit": "bytes",
}

metric_info["mem_lnx_slab"] = {
    "title": _("Slab (Various smaller caches)"),
    "color": "#af91eb",
    "unit": "bytes",
}

metric_info["mem_lnx_sreclaimable"] = {
    "title": _("Reclaimable memory"),
    "color": "23/a",
    "unit": "bytes",
}

metric_info["mem_lnx_sunreclaim"] = {
    "title": _("Unreclaimable memory"),
    "color": "24/a",
    "unit": "bytes",
}

metric_info["mem_lnx_pending"] = {
    "title": _("Pending memory"),
    "color": "25/a",
    "unit": "bytes",
}

metric_info["mem_lnx_unevictable"] = {
    "title": _("Unevictable memory"),
    "color": "26/a",
    "unit": "bytes",
}

metric_info["mem_lnx_anon_pages"] = {
    "title": _("Anonymous pages"),
    "color": "#cc4040",
    "unit": "bytes",
}

metric_info["mem_lnx_active_anon"] = {
    "title": _("Active (anonymous)"),
    "color": "#ff4040",
    "unit": "bytes",
}

metric_info["mem_lnx_active_file"] = {
    "title": _("Active (files)"),
    "color": "#ff8080",
    "unit": "bytes",
}

metric_info["mem_lnx_inactive_anon"] = {
    "title": _("Inactive (anonymous)"),
    "color": "#377cab",
    "unit": "bytes",
}

metric_info["mem_lnx_inactive_file"] = {
    "title": _("Inactive (files)"),
    "color": "#4eb0f2",
    "unit": "bytes",
}

metric_info["mem_lnx_active"] = {
    "title": _("Active"),
    "color": "#ff4040",
    "unit": "bytes",
}

metric_info["mem_lnx_inactive"] = {
    "title": _("Inactive"),
    "color": "#4040ff",
    "unit": "bytes",
}

metric_info["mem_lnx_dirty"] = {
    "title": _("Dirty disk blocks"),
    "color": "#f2904e",
    "unit": "bytes",
}

metric_info["mem_lnx_writeback"] = {
    "title": _("Currently being written"),
    "color": "#f2df40",
    "unit": "bytes",
}

metric_info["mem_lnx_nfs_unstable"] = {
    "title": _("Modified NFS data"),
    "color": "#c6f24e",
    "unit": "bytes",
}

metric_info["mem_lnx_bounce"] = {
    "title": _("Bounce buffers"),
    "color": "#4ef26c",
    "unit": "bytes",
}

metric_info["mem_lnx_writeback_tmp"] = {
    "title": _("Dirty FUSE data"),
    "color": "#4eeaf2",
    "unit": "bytes",
}

metric_info["mem_lnx_total_total"] = {
    "title": _("Total virtual memory"),
    "color": "#f0f0f0",
    "unit": "bytes",
}

metric_info["mem_lnx_committed_as"] = {
    "title": _("Committed memory"),
    "color": "#40a080",
    "unit": "bytes",
}

metric_info["mem_lnx_commit_limit"] = {
    "title": _("Commit limit"),
    "color": "#e0e0e0",
    "unit": "bytes",
}

metric_info["mem_lnx_shmem"] = {
    "title": _("Shared memory"),
    "color": "#bf9111",
    "unit": "bytes",
}

metric_info["mem_lnx_kernel_stack"] = {
    "title": _("Kernel stack"),
    "color": "#7192ad",
    "unit": "bytes",
}

metric_info["mem_lnx_page_tables"] = {
    "title": _("Page tables"),
    "color": "#71ad9f",
    "unit": "bytes",
}

metric_info["mem_lnx_mlocked"] = {
    "title": _("Locked mmap() data"),
    "color": "#a671ad",
    "unit": "bytes",
}

metric_info["mem_lnx_mapped"] = {
    "title": _("Mapped data"),
    "color": "#a671ad",
    "unit": "bytes",
}

metric_info["mem_lnx_anon_huge_pages"] = {
    "title": _("Anonymous huge pages"),
    "color": "#f0f0f0",
    "unit": "bytes",
}

metric_info["mem_lnx_huge_pages_total"] = {
    "title": _("Huge pages total"),
    "color": "#f0f0f0",
    "unit": "bytes",
}

metric_info["mem_lnx_huge_pages_free"] = {
    "title": _("Huge pages free"),
    "color": "#f0a0f0",
    "unit": "bytes",
}

metric_info["mem_lnx_huge_pages_rsvd"] = {
    "title": _("Huge pages reserved part of free"),
    "color": "#40f0f0",
    "unit": "bytes",
}

metric_info["mem_lnx_huge_pages_surp"] = {
    "title": _("Huge pages surplus"),
    "color": "#90f0b0",
    "unit": "bytes",
}

metric_info["mem_lnx_vmalloc_total"] = {
    "title": _("Total address space"),
    "color": "#f0f0f0",
    "unit": "bytes",
}

metric_info["mem_lnx_vmalloc_used"] = {
    "title": _("Allocated space"),
    "color": "#aaf76f",
    "unit": "bytes",
}

metric_info["mem_lnx_vmalloc_chunk"] = {
    "title": _("Largest free chunk"),
    "color": "#c6f7e9",
    "unit": "bytes",
}

metric_info["mem_lnx_hardware_corrupted"] = {
    "title": _("Hardware corrupted memory"),
    "color": "13/a",
    "unit": "bytes",
}

# Consumed Host Memory usage is defined as the amount of host memory that is allocated to the virtual machine
metric_info["mem_esx_host"] = {
    "title": _("Consumed host memory"),
    "color": "#70f038",
    "unit": "bytes",
}

# Active Guest Memory is defined as the amount of guest memory that is currently being used by the guest operating system and its applications
metric_info["mem_esx_guest"] = {
    "title": _("Active guest memory"),
    "color": "15/a",
    "unit": "bytes",
}

metric_info["mem_esx_ballooned"] = {
    "title": _("Ballooned memory"),
    "color": "21/a",
    "unit": "bytes",
}

metric_info["mem_esx_shared"] = {
    "title": _("Shared memory"),
    "color": "34/a",
    "unit": "bytes",
}

metric_info["mem_esx_private"] = {
    "title": _("Private memory"),
    "color": "25/a",
    "unit": "bytes",
}

metric_info["pagefile_total"] = {
    "title": _("Pagefile installed"),
    "color": "#e0e0e0",
    "unit": "bytes",
}

metric_info["mem_heap"] = {
    "title": _("Heap memory usage"),
    "unit": "bytes",
    "color": "23/a",
}

metric_info["mem_heap_committed"] = {
    "title": _("Heap memory committed"),
    "unit": "bytes",
    "color": "23/b",
}

metric_info["mem_nonheap"] = {
    "title": _("Non-heap memory usage"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["mem_nonheap_committed"] = {
    "title": _("Non-heap memory committed"),
    "unit": "bytes",
    "color": "16/b",
}

metric_info["tapes_total"] = {
    "title": _("Total number of tapes"),
    "unit": "count",
    "color": "36/a",
}

metric_info["tapes_free"] = {
    "title": _("Free tapes"),
    "unit": "count",
    "color": "45/b",
}

metric_info["tapes_util"] = {
    "title": _("Tape utilization"),
    "unit": "count",
    "color": "33/a",
}

metric_info["inodes_used"] = {
    "title": _("Used inodes"),
    "unit": "count",
    "color": "#a0608f",
}

metric_info["shared_locks"] = {
    "title": _("Shared locks"),
    "unit": "count",
    "color": "#92ec89",
}

metric_info["exclusive_locks"] = {
    "title": _("Exclusive locks"),
    "unit": "count",
    "color": "#ca5706",
}

metric_info["disk_read_throughput"] = {
    "title": _("Read throughput"),
    "unit": "bytes/s",
    "color": "#40c080",
}

metric_info["disk_write_throughput"] = {
    "title": _("Write throughput"),
    "unit": "bytes/s",
    "color": "#4080c0",
}

metric_info["disk_ios"] = {
    "title": _("Disk I/O operations"),
    "unit": "1/s",
    "color": "#60e0a0",
}

metric_info["disk_read_ios"] = {
    "title": _("Read operations"),
    "unit": "1/s",
    "color": "#60e0a0",
}

metric_info["disk_write_ios"] = {
    "title": _("Write operations"),
    "unit": "1/s",
    "color": "#60a0e0",
}

metric_info["disk_average_read_wait"] = {
    "title": _("Read wait time"),
    "unit": "s",
    "color": "#20e8c0",
}

metric_info["disk_min_read_wait"] = {
    "title": _("Minimum read wait time"),
    "unit": "s",
    "color": "#20e8a0",
}

metric_info["disk_max_read_wait"] = {
    "title": _("Maximum read wait time"),
    "unit": "s",
    "color": "#20e8e0",
}

metric_info["disk_average_write_wait"] = {
    "title": _("Write wait time"),
    "unit": "s",
    "color": "#20c0e8",
}

metric_info["disk_min_write_wait"] = {
    "title": _("Minimum write wait time"),
    "unit": "s",
    "color": "#20a0e8",
}

metric_info["disk_max_write_wait"] = {
    "title": _("Maximum write wait time"),
    "unit": "s",
    "color": "#20e0e8",
}

metric_info["disk_average_wait"] = {
    "title": _("Request wait time"),
    "unit": "s",
    "color": "#4488cc",
}

metric_info["disk_average_read_request_size"] = {
    "title": _("Average read request size"),
    "unit": "bytes",
    "color": "#409c58",
}

metric_info["disk_average_write_request_size"] = {
    "title": _("Average write request size"),
    "unit": "bytes",
    "color": "#40589c",
}

metric_info["disk_average_request_size"] = {
    "title": _("Average request size"),
    "unit": "bytes",
    "color": "#4488cc",
}

metric_info["disk_latency"] = {
    "title": _("Average disk latency"),
    "unit": "s",
    "color": "#c04080",
}

metric_info["disk_read_latency"] = {
    "title": _("Disk read latency"),
    "unit": "s",
    "color": "#40c080",
}

metric_info["disk_write_latency"] = {
    "title": _("Disk write latency"),
    "unit": "s",
    "color": "#4080c0",
}

metric_info["read_latency"] = {
    "title": _("Read latency"),
    "unit": "s",
    "color": "35/a",
}

metric_info["read_hits"] = {
    "title": _("Read hits"),
    "unit": "%",
    "color": "31/a",
}

metric_info["write_latency"] = {
    "title": _("Write latency"),
    "unit": "s",
    "color": "45/a",
}

metric_info["other_latency"] = {
    "title": _("Other latency"),
    "unit": "s",
    "color": "21/a",
}

metric_info["disk_queue_length"] = {
    "title": _("Average disk I/O-queue length"),
    "unit": "",
    "color": "35/a",
}

metric_info["disk_read_ql"] = {
    "title": _("Average disk read queue length"),
    "unit": "",
    "color": "45/a",
}

metric_info["disk_write_ql"] = {
    "title": _("Average disk write queue length"),
    "unit": "",
    "color": "#7060b0",
}

metric_info["disk_utilization"] = {
    "title": _("Disk utilization"),
    "unit": "%",
    "color": "#a05830",
}

metric_info["disk_capacity"] = {
    "title": _("Total disk capacity"),
    "unit": "bytes",
    "color": "12/a",
}

metric_info["disks"] = {
    "title": _("Disks"),
    "unit": "count",
    "color": "41/a",
}

metric_info["spare_disks"] = {
    "title": _("Spare disk"),
    "unit": "count",
    "color": "26/a",
}

metric_info["failed_disks"] = {
    "title": _("Failed disk"),
    "unit": "count",
    "color": "13/a",
}

metric_info["read_blocks"] = {
    "title": _("Read blocks per second"),
    "unit": "1/s",
    "color": "11/a",
}

metric_info["write_blocks"] = {
    "title": _("Write blocks per second"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["files_open"] = {
    "title": _("Open files"),
    "unit": "count",
    "color": "#ff6234",
}

metric_info["directories"] = {
    "title": _("Directories"),
    "unit": "count",
    "color": "#202020",
}

metric_info["shared_memory_segments"] = {
    "title": _("Shared memory segments"),
    "unit": "count",
    "color": "#606060",
}

metric_info["semaphore_ids"] = {
    "title": _("IPC semaphore IDs"),
    "unit": "count",
    "color": "#404040",
}

metric_info["semaphores"] = {
    "title": _("IPC semaphores"),
    "unit": "count",
    "color": "#ff4534",
}

metric_info["backup_size"] = {
    "title": _("Backup size"),
    "unit": "bytes",
    "color": "12/a",
}

metric_info["backup_avgspeed"] = {
    "title": _("Average speed of backup"),
    "unit": "bytes/s",
    "color": "22/a",
}

metric_info["backup_duration"] = {
    "title": _("Duration of backup"),
    "unit": "s",
    "color": "33/a",
}

metric_info["readsize"] = {
    "title": _("Readsize"),
    "unit": "bytes",
    "color": "12/a",
}

metric_info["transferredsize"] = {
    "title": _("Transferredsize"),
    "unit": "bytes",
    "color": "12/a",
}

metric_info["job_duration"] = {
    "title": _("Job duration"),
    "unit": "s",
    "color": "33/a",
}

metric_info["backup_age_database"] = {
    "title": _("Age of last database backup"),
    "unit": "s",
    "color": "11/a",
}

metric_info["backup_age_database_diff"] = {
    "title": _("Age of last differential database backup"),
    "unit": "s",
    "color": "14/a",
}

metric_info["backup_age_log"] = {
    "title": _("Age of last log backup"),
    "unit": "s",
    "color": "21/a",
}

metric_info["backup_age_file_or_filegroup"] = {
    "title": _("Age of last file or filegroup backup"),
    "unit": "s",
    "color": "24/a",
}

metric_info["backup_age_file_diff"] = {
    "title": _("Age of last differential file backup"),
    "unit": "s",
    "color": "31/a",
}

metric_info["backup_age_partial"] = {
    "title": _("Age of last partial backup"),
    "unit": "s",
    "color": "34/a",
}

metric_info["backup_age_differential_partial"] = {
    "title": _("Age of last differential partial backup"),
    "unit": "s",
    "color": "41/a",
}

metric_info["backup_age"] = {
    "title": _("Time since last backup"),
    "unit": "s",
    "color": "34/a",
}

metric_info["file_age_oldest"] = {
    "title": _("Oldest file"),
    "unit": "s",
    "color": "11/a",
}

metric_info["file_age_newest"] = {
    "title": _("Newest file"),
    "unit": "s",
    "color": "13/a",
}

metric_info["logswitches_last_hour"] = {
    "title": _("Log switches in the last 60 minutes"),
    "unit": "count",
    "color": "#006040",
}

metric_info["direct_io"] = {
    "title": _("Direct I/O"),
    "unit": "bytes/s",
    "color": "21/a",
}

metric_info["buffered_io"] = {
    "title": _("Buffered I/O"),
    "unit": "bytes/s",
    "color": "23/a",
}

metric_info["write_cache_usage"] = {
    "title": _("Write cache usage"),
    "unit": "%",
    "color": "#030303",
}

metric_info["total_cache_usage"] = {
    "title": _("Total cache usage"),
    "unit": "%",
    "color": "#0ae86d",
}

metric_info["nfs_ios"] = {
    "title": _("NFS operations"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["nfsv4_ios"] = {
    "title": _("NFSv4 operations"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["nfsv4_1_ios"] = {
    "title": _("NFSv4.1 operations"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["harddrive_power_cycles"] = {
    "title": _("Harddrive power cycles"),
    "unit": "count",
    "color": "11/a",
}

metric_info["harddrive_reallocated_sectors"] = {
    "title": _("Harddrive reallocated sectors"),
    "unit": "count",
    "color": "14/a",
}

metric_info["harddrive_reallocated_events"] = {
    "title": _("Harddrive reallocated events"),
    "unit": "count",
    "color": "21/a",
}

metric_info["harddrive_spin_retries"] = {
    "title": _("Harddrive spin retries"),
    "unit": "count",
    "color": "24/a",
}

metric_info["harddrive_pending_sectors"] = {
    "title": _("Harddrive pending sectors"),
    "unit": "count",
    "color": "31/a",
}

metric_info["harddrive_cmd_timeouts"] = {
    "title": _("Harddrive command timeouts"),
    "unit": "count",
    "color": "34/a",
}

metric_info["harddrive_end_to_end_errors"] = {
    "title": _("Harddrive end-to-end errors"),
    "unit": "count",
    "color": "41/a",
}

metric_info["harddrive_uncorrectable_erros"] = {
    "title": _("Harddrive uncorrectable errors"),
    "unit": "count",
    "color": "44/a",
}

metric_info["harddrive_udma_crc_errors"] = {
    "title": _("Harddrive UDMA CRC errors"),
    "unit": "count",
    "color": "46/a",
}

metric_info["harddrive_crc_errors"] = {
    "title": _("Harddrive CRC errors"),
    "unit": "count",
    "color": "15/a",
}

metric_info["harddrive_uncorrectable_errors"] = {
    "title": _("Harddrive uncorrectable errors"),
    "unit": "count",
    "color": "13/a",
}

metric_info["nvme_media_and_data_integrity_errors"] = {
    "title": _("Media and data integrity errors"),
    "unit": "count",
    "color": "11/a",
}

metric_info["nvme_error_information_log_entries"] = {
    "title": _("Error information log entries"),
    "unit": "count",
    "color": "14/a",
}

metric_info["nvme_critical_warning"] = {
    "title": _("Critical warning"),
    "unit": "count",
    "color": "14/a",
}

metric_info["nvme_available_spare"] = {
    "title": _("Available Spare"),
    "unit": "%",
    "color": "21/a",
}

metric_info["nvme_spare_percentage_used"] = {
    "title": _("Percentage used"),
    "unit": "%",
    "color": "24/a",
}

metric_info["nvme_data_units_read"] = {
    "title": _("Data units read"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["nvme_data_units_written"] = {
    "title": _("Data units written"),
    "unit": "bytes",
    "color": "24/a",
}

metric_info["data_usage"] = {
    "title": _("Data usage"),
    "unit": "%",
    "color": "21/a",
}

metric_info["meta_usage"] = {
    "title": _("Meta usage"),
    "unit": "%",
    "color": "31/a",
}

metric_info["storage_processor_util"] = {
    "title": _("Storage Processor Utilization"),
    "unit": "%",
    "color": "34/a",
}

metric_info["storage_used"] = {
    "title": _("Storage space used"),
    "unit": "bytes",
    "color": "36/a",
}

metric_info["storage_percent"] = {
    "title": _("Storage space used"),
    "unit": "%",
    "color": "36/b",
}

metric_info["filehandler_perc"] = {
    "title": _("Used file handles"),
    "unit": "%",
    "color": "#4800ff",
}

metric_info["capacity_perc"] = {
    "title": _("Available capacity"),
    "unit": "%",
    "color": "#4800ff",
}

metric_info["available_file_descriptors"] = {
    "title": _("Number of available file descriptors"),
    "unit": "count",
    "color": "21/a",
}

metric_info["mem_total_virtual_in_bytes"] = {
    "title": _("Total virtual memory"),
    "unit": "bytes",
    "color": "53/a",
}

metric_info["store_size"] = {
    "title": _("Store size"),
    "unit": "bytes",
    "color": "32/a",
}

metric_info["id_cache_size"] = {
    "title": _("ID cache size"),
    "unit": "bytes",
    "color": "25/a",
}

metric_info["field_data_size"] = {
    "title": _("Field data size"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["avg_doc_size"] = {
    "title": _("Average document size"),
    "unit": "bytes",
    "color": "25/b",
}

metric_info["disk_fill_rate"] = {
    "title": _("Disk fill rate"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["disk_drain_rate"] = {
    "title": _("Disk drain rate"),
    "unit": "1/s",
    "color": "31/b",
}

metric_info["memory_used"] = {
    "color": "46/a",
    "title": _("Memory used"),
    "unit": "bytes",
}

# In order to use the "bytes" unit we would have to change the output of the check, (i.e. divide by
# 1024) which means an invalidation of historic values.
metric_info["kb_out_of_sync"] = {
    "title": _("KiB out of sync"),  # according to documentation
    "unit": "count",
    "color": "14/a",
}

metric_info["log_file_utilization"] = {
    "title": _("Percentage of log file used"),
    "unit": "%",
    "color": "42/a",
}

metric_info["checkpoint_age"] = {
    "title": _("Time since last checkpoint"),
    "unit": "s",
    "color": "#006040",
}

# .
#   .--Graphs--------------------------------------------------------------.
#   |                    ____                 _                            |
#   |                   / ___|_ __ __ _ _ __ | |__  ___                    |
#   |                  | |  _| '__/ _` | '_ \| '_ \/ __|                   |
#   |                  | |_| | | | (_| | |_) | | | \__ \                   |
#   |                   \____|_|  \__,_| .__/|_| |_|___/                   |
#   |                                  |_|                                 |
#   +----------------------------------------------------------------------+
#   |  Definitions of time series graphs                                   |
#   '----------------------------------------------------------------------'

graph_info["read_and_written_blocks"] = {
    "title": _("Read and written blocks"),
    "metrics": [
        ("read_blocks", "area"),
        ("write_blocks", "-area"),
    ],
}

graph_info["disk_rw_latency"] = {
    "title": _("Disk latency"),
    "metrics": [("disk_read_latency", "area"), ("disk_write_latency", "-area")],
}

# TODO: is this still used?
graph_info["disk_latency"] = {
    "title": _("Disk latency"),
    "metrics": [("read_latency", "area"), ("write_latency", "-area")],
}

graph_info["read_write_queue_length"] = {
    "title": _("Read / Write queue length"),
    "metrics": [("disk_read_ql", "area"), ("disk_write_ql", "-area")],
}

graph_info["backup_time"] = {
    "title": _("Backup time"),
    "metrics": [("checkpoint_age", "area"), ("backup_age", "stack")],
}

graph_info["total_cache_usage"] = {
    "title": _("Total cache usage"),
    "metrics": [("total_cache_usage", "area")],
    "range": (0, 100),
}

graph_info["write_cache_usage"] = {
    "title": _("Write cache usage"),
    "metrics": [("write_cache_usage", "area")],
    "range": (0, 100),
}

graph_info["zfs_meta_data"] = {
    "title": _("ZFS meta data"),
    "metrics": [
        ("zfs_metadata_max", "area"),
        ("zfs_metadata_used", "area"),
        ("zfs_metadata_limit", "line"),
    ],
}

graph_info["cache_hit_ratio"] = {
    "title": _("Cache hit ratio"),
    "metrics": [
        ("cache_hit_ratio", "area"),
        ("prefetch_metadata_hit_ratio", "line"),
        ("prefetch_data_hit_ratio", "area"),
    ],
}

graph_info["wasted_space_of_tables_and_indexes"] = {
    "title": _("Wasted space of tables and indexes"),
    "metrics": [
        ("tablespace_wasted", "area"),
        ("indexspace_wasted", "stack"),
    ],
}

# diskstat checks

graph_info["disk_utilization"] = {
    "title": _("Disk utilization"),
    "metrics": [
        ("disk_utilization", "area"),
    ],
    "range": (0, 100),
    "scalars": [
        "disk_utilization:warn",
        "disk_utilization:crit",
    ],
}

graph_info["disk_throughput"] = {
    "title": _("Disk throughput"),
    "metrics": [
        ("disk_read_throughput", "area"),
        ("disk_write_throughput", "-area"),
    ],
    "scalars": [
        ("disk_read_throughput:warn", "Warning read"),
        ("disk_read_throughput:crit", "Critical read"),
        ("disk_write_throughput:warn,-1,*", "Warning write"),
        ("disk_write_throughput:crit,-1,*", "Critical write"),
    ],
}

graph_info["disk_io_operations"] = {
    "title": _("Disk I/O operations"),
    "metrics": [
        ("disk_read_ios", "area"),
        ("disk_write_ios", "-area"),
    ],
}

graph_info["direct_and_buffered_io_operations"] = {
    "title": _("Direct and buffered I/O operations"),
    "metrics": [
        ("direct_io", "stack"),
        ("buffered_io", "stack"),
    ],
}

graph_info["average_request_size"] = {
    "title": _("Average request size"),
    "metrics": [
        ("disk_average_read_request_size", "area"),
        ("disk_average_write_request_size", "-area"),
    ],
}

graph_info["average_end_to_end_wait_time"] = {
    "title": _("Average end to end wait time"),
    "metrics": [
        ("disk_average_read_wait", "area"),
        ("disk_average_write_wait", "-area"),
    ],
}

graph_info["spare_and_broken_disks"] = {
    "title": _("Spare and broken disks"),
    "metrics": [
        ("disks", "area"),
        ("spare_disks", "stack"),
        ("failed_disks", "stack"),
    ],
}

graph_info["database_sizes"] = {
    "title": _("Database sizes"),
    "metrics": [
        ("database_size", "area"),
        ("unallocated_size", "stack"),
        ("reserved_size", "stack"),
        ("data_size", "stack"),
        ("indexes_size", "stack"),
        ("unused_size", "stack"),
        ("database_reclaimable", "stack"),
    ],
    "optional_metrics": [
        "unallocated_size",
        "reserved_size",
        "data_size",
        "indexes_size",
        "unused_size",
        "database_reclaimable",
    ],
}

graph_info["number_of_shared_and_exclusive_locks"] = {
    "title": _("Number of shared and exclusive locks"),
    "metrics": [
        ("shared_locks", "area"),
        ("exclusive_locks", "stack"),
    ],
}

graph_info["tablespace_sizes"] = {
    "title": _("Tablespace sizes"),
    "metrics": [
        ("tablespace_size", "area"),
        ("tablespace_used", "area"),
    ],
    "scalars": [
        "tablespace_size:warn",
        "tablespace_size:crit",
    ],
    "range": (0, "tablespace_max_size"),
}

graph_info["ram_swap_used"] = {
    "title": _("RAM + Swap used"),
    "metrics": [
        ("mem_used", "area"),
        ("swap_used", "stack"),
    ],
    "conflicting_metrics": ["swap_total"],
    "scalars": [
        ("swap_used:max,mem_used:max,+#008080", _("Total RAM + Swap installed")),
        ("mem_used:max#80ffff", _("Total RAM installed")),
    ],
    "range": (0, "swap_used:max,mem_used:max,+"),
}

graph_info["mem_used_percent"] = {
    "title": _("Used RAM"),
    "metrics": [
        ("mem_used_percent", "area"),
    ],
    "scalars": [
        "mem_used_percent:warn",
        "mem_used_percent:crit",
    ],
    "range": (0, 100),
}

graph_info["cpu_mem_used_percent"] = {
    "title": _("Used CPU Memory"),
    "metrics": [
        ("cpu_mem_used_percent", "area"),
    ],
    "scalars": ["cpu_mem_used_percent:warn", "cpu_mem_used_percent:crit"],
    "range": (0, 100),
}

graph_info["mem_trend"] = {
    "title": _("Trend of memory usage growth"),
    "metrics": [
        ("mem_trend", "line"),
    ],
}

graph_info["mem_growing"] = {
    "title": _("Growing"),
    "metrics": [
        (
            "mem_growth.max,0,MAX",
            "area",
            _("Growth"),
        ),
    ],
}

graph_info["mem_shrinking"] = {
    "title": _("Shrinking"),
    "consolidation_function": "min",
    "metrics": [
        ("mem_growth.min,0,MIN,-1,*#299dcf", "-area", _("Shrinkage")),
    ],
}

# Linux memory graphs. They are a lot...

graph_info["ram_swap_overview"] = {
    "title": _("RAM + Swap overview"),
    "metrics": [
        ("mem_total", "area"),
        ("swap_total", "stack"),
        ("mem_used", "area"),
        ("swap_used", "stack"),
    ],
}

graph_info["swap"] = {
    "title": _("Swap"),
    "metrics": [
        ("swap_total", "area"),
        ("swap_used", "area"),
        ("swap_cached", "stack"),
    ],
}

graph_info["caches"] = {
    "title": _("Caches"),
    "metrics": [
        ("mem_lnx_slab", "stack"),
        ("swap_cached", "stack"),
        ("mem_lnx_buffers", "stack"),
        ("mem_lnx_cached", "stack"),
    ],
}

graph_info["active_and_inactive_memory_anon"] = {
    "title": _("Active and Inactive Memory"),
    "metrics": [
        ("mem_lnx_inactive_anon", "stack"),
        ("mem_lnx_inactive_file", "stack"),
        ("mem_lnx_active_anon", "stack"),
        ("mem_lnx_active_file", "stack"),
    ],
}

# TODO: Show this graph only, if the previous graph
# is not possible. This cannot be done with a condition,
# since we currently cannot state a condition on non-existing
# metrics.
graph_info["active_and_inactive_memory"] = {
    "title": _("Active and Inactive Memory"),
    "metrics": [
        ("mem_lnx_active", "area"),
        ("mem_lnx_inactive", "area"),
    ],
    "conflicting_metrics": ["mem_lnx_active_anon"],
}

graph_info["ram_used"] = {
    "title": _("RAM used"),
    "metrics": [
        ("mem_used", "area"),
    ],
    "conflicting_metrics": ["swap_used"],
    "scalars": [
        ("mem_used:max#000000", "Maximum"),
        ("mem_used:warn", "Warning"),
        ("mem_used:crit", "Critical"),
    ],
    "range": (0, "mem_used:max"),
}

graph_info["commit_charge"] = {
    "title": _("Commit Charge"),
    "metrics": [
        ("pagefile_used", "area"),
    ],
    "scalars": [
        ("pagefile_used:max#000000", "Maximum"),
        ("pagefile_used:warn", "Warning"),
        ("pagefile_used:crit", "Critical"),
    ],
    "range": (0, "pagefile_used:max"),
}

graph_info["filesystem_writeback"] = {
    "title": _("Filesystem Writeback"),
    "metrics": [
        ("mem_lnx_dirty", "area"),
        ("mem_lnx_writeback", "stack"),
        ("mem_lnx_nfs_unstable", "stack"),
        ("mem_lnx_bounce", "stack"),
        ("mem_lnx_writeback_tmp", "stack"),
    ],
}

graph_info["memory_committing"] = {
    "title": _("Memory committing"),
    "metrics": [
        ("mem_lnx_total_total", "area"),
        ("mem_lnx_committed_as", "area"),
        ("mem_lnx_commit_limit", "stack"),
    ],
}

graph_info["memory_that_cannot_be_swapped_out"] = {
    "title": _("Memory that cannot be swapped out"),
    "metrics": [
        ("mem_lnx_kernel_stack", "area"),
        ("mem_lnx_page_tables", "stack"),
        ("mem_lnx_mlocked", "stack"),
    ],
}

graph_info["huge_pages"] = {
    "title": _("Huge Pages"),
    "metrics": [
        ("mem_lnx_huge_pages_total", "area"),
        ("mem_lnx_huge_pages_free", "area"),
        ("mem_lnx_huge_pages_rsvd", "area"),
        ("mem_lnx_huge_pages_surp", "line"),
    ],
}

graph_info["vmalloc_address_space_1"] = {
    "title": _("VMalloc Address Space"),
    "metrics": [
        ("mem_lnx_vmalloc_total", "area"),
        ("mem_lnx_vmalloc_used", "area"),
        ("mem_lnx_vmalloc_chunk", "stack"),
    ],
}

# TODO: Warum ohne total? Dürfte eigentlich nicht
# vorkommen.
graph_info["vmalloc_address_space_2"] = {
    "title": _("VMalloc Address Space"),
    "metrics": [
        ("mem_lnx_vmalloc_used", "area"),
        ("mem_lnx_vmalloc_chunk", "stack"),
    ],
}

graph_info["heap_and_non_heap_memory"] = {
    "title": _("Heap and non-heap memory"),
    "metrics": [
        ("mem_heap", "area"),
        ("mem_nonheap", "stack"),
    ],
    "conflicting_metrics": [
        "mem_heap_committed",
        "mem_nonheap_committed",
    ],
}

graph_info["heap_memory_usage"] = {
    "title": _("Heap memory usage"),
    "metrics": [
        ("mem_heap_committed", "area"),
        ("mem_heap", "area"),
    ],
    "scalars": [
        "mem_heap:warn",
        "mem_heap:crit",
    ],
}

graph_info["non-heap_memory_usage"] = {
    "title": _("Non-heap memory usage"),
    "metrics": [
        ("mem_nonheap_committed", "area"),
        ("mem_nonheap", "area"),
    ],
    "scalars": [
        "mem_nonheap:warn",
        "mem_nonheap:crit",
        "mem_nonheap:max",
    ],
}

graph_info["private_and_shared_memory"] = {
    "title": _("Private and shared memory"),
    "metrics": [
        ("mem_esx_shared", "area"),
        ("mem_esx_private", "area"),
    ],
}

graph_info["harddrive_health_statistic"] = {
    "title": _("Harddrive health statistic"),
    "metrics": [
        ("harddrive_power_cycles", "stack"),
        ("harddrive_reallocated_sectors", "stack"),
        ("harddrive_reallocated_events", "stack"),
        ("harddrive_spin_retries", "stack"),
        ("harddrive_pending_sectors", "stack"),
        ("harddrive_cmd_timeouts", "stack"),
        ("harddrive_end_to_end_errors", "stack"),
        ("harddrive_uncorrectable_errors", "stack"),
        ("harddrive_udma_crc_errors", "stack"),
    ],
}

graph_info["mem_perm_used"] = {
    "title": _("Permanent Generation Memory"),
    "metrics": [("mem_perm_used", "area")],
    "scalars": [
        "mem_perm_used:warn",
        "mem_perm_used:crit",
        ("mem_perm_used:max#000000", _("Max Perm used")),
    ],
    "range": (0, "mem_perm_used:max"),
}

graph_info["datafile_sizes"] = {
    "title": _("Datafile Sizes"),
    "metrics": [("allocated_size", "line"), ("data_size", "area")],
}

graph_info["files_notification_spool"] = {
    "title": _("Amount of files in notification spool"),
    "metrics": [
        ("new_files", "area"),
        ("deferred_files", "area"),
        ("corrupted_files", "area"),
    ],
    "optional_metrics": ["deferred_files", "corrupted_files"],
}
