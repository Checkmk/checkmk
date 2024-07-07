#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._utils import graph_info, metric_info
from cmk.gui.i18n import _

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

metric_info["streams"] = {
    "title": _("Streams"),
    "unit": "%",
    "color": "35/a",
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

metric_info["cpu_mem_used_percent"] = {
    "color": "#80ff40",
    "title": _("CPU Memory used"),
    "unit": "%",
}

metric_info["mem_perm_used"] = {
    "color": "#80ff40",
    "title": _("Permanent generation memory"),
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

metric_info["mem_pages_rate"] = {
    "title": _("Memory pages"),
    "unit": "1/s",
    "color": "34/a",
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
    "color": "#1e8fff",
    "unit": "bytes",
}

metric_info["mem_lnx_committed_as"] = {
    "title": _("Committed memory"),
    "color": "#32a852",
    "unit": "bytes",
}

metric_info["mem_lnx_commit_limit"] = {
    "title": _("Commit limit"),
    "color": "#ff64ff",
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

metric_info["disk_ios"] = {
    "title": _("Disk I/O operations"),
    "unit": "1/s",
    "color": "#60e0a0",
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

metric_info["job_duration"] = {
    "title": _("Job duration"),
    "unit": "s",
    "color": "33/a",
}

metric_info["backup_age"] = {
    "title": _("Time since last backup"),
    "unit": "s",
    "color": "34/a",
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

metric_info["harddrive_udma_crc_errors"] = {
    "title": _("Harddrive UDMA CRC errors"),
    "unit": "count",
    "color": "46/a",
}

metric_info["harddrive_uncorrectable_errors"] = {
    "title": _("Harddrive uncorrectable errors"),
    "unit": "count",
    "color": "13/a",
}

metric_info["storage_processor_util"] = {
    "title": _("Storage processor utilization"),
    "unit": "%",
    "color": "34/a",
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

metric_info["io_consumption_percent"] = {
    "title": _("Storage IO consumption"),
    "unit": "%",
    "color": "25/b",
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
        ("zfs_metadata_max", "line"),
        ("zfs_metadata_used", "line"),
        ("zfs_metadata_limit", "line"),
    ],
}

graph_info["cache_hit_ratio"] = {
    "title": _("Cache hit ratio"),
    "metrics": [
        ("cache_hit_ratio", "line"),
        ("prefetch_metadata_hit_ratio", "line"),
        ("prefetch_data_hit_ratio", "line"),
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

graph_info["direct_and_buffered_io_operations"] = {
    "title": _("Direct and buffered I/O operations"),
    "metrics": [
        ("direct_io", "stack"),
        ("buffered_io", "stack"),
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
        ("tablespace_size", "line"),
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
        ("mem_used", "stack"),
        ("swap_used", "stack"),
    ],
    "conflicting_metrics": ["swap_total"],
    "scalars": [
        ("swap_used:max,mem_used:max,+#008080", _("Total RAM + Swap installed")),
        ("mem_used:max#80ffff", _("Total RAM installed")),
    ],
    "range": (0, "swap_used:max,mem_used:max,+"),
}

graph_info["cpu_mem_used_percent"] = {
    "title": _("Used CPU memory"),
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
    "title": _("RAM + swap overview"),
    "metrics": [
        ("mem_total,swap_total,+#87cefa", "area", _("RAM + swap installed")),
        ("mem_used,swap_used,+#37fa37", "line", _("RAM + swap used")),
    ],
}

graph_info["swap"] = {
    "title": _("Swap"),
    "metrics": [
        ("swap_total", "line"),
        ("swap_used", "stack"),
        ("swap_cached", "stack"),
    ],
}

graph_info["active_and_inactive_memory_anon"] = {
    "title": _("Active and inactive memory"),
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
    "title": _("Active and inactive memory"),
    "metrics": [
        ("mem_lnx_active", "stack"),
        ("mem_lnx_inactive", "stack"),
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


graph_info["filesystem_writeback"] = {
    "title": _("Filesystem writeback"),
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
        ("mem_lnx_total_total", "line"),
        ("mem_lnx_committed_as", "stack"),
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
    "title": _("Huge pages"),
    "metrics": [
        ("mem_lnx_huge_pages_total", "line"),
        ("mem_lnx_huge_pages_free", "stack"),
        ("mem_lnx_huge_pages_rsvd", "stack"),
        ("mem_lnx_huge_pages_surp", "line"),
    ],
}

graph_info["vmalloc_address_space_1"] = {
    "title": _("VMalloc address space"),
    "metrics": [
        ("mem_lnx_vmalloc_total", "line"),
        ("mem_lnx_vmalloc_used", "stack"),
        ("mem_lnx_vmalloc_chunk", "stack"),
    ],
}

# TODO: Warum ohne total? Dürfte eigentlich nicht
# vorkommen.
graph_info["vmalloc_address_space_2"] = {
    "title": _("VMalloc address space"),
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
        ("mem_heap_committed", "line"),
        ("mem_heap", "line"),
    ],
    "scalars": [
        "mem_heap:warn",
        "mem_heap:crit",
    ],
}

graph_info["non-heap_memory_usage"] = {
    "title": _("Non-heap memory usage"),
    "metrics": [
        ("mem_nonheap_committed", "line"),
        ("mem_nonheap", "line"),
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
        ("mem_esx_shared", "stack"),
        ("mem_esx_private", "stack"),
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
    "title": _("Permanent generation memory"),
    "metrics": [("mem_perm_used", "area")],
    "scalars": [
        "mem_perm_used:warn",
        "mem_perm_used:crit",
        ("mem_perm_used:max#000000", _("Max Perm used")),
    ],
    "range": (0, "mem_perm_used:max"),
}

graph_info["datafile_sizes"] = {
    "title": _("Datafile sizes"),
    "metrics": [("allocated_size", "line"), ("data_size", "area")],
}

# workaround for showing single metrics of multiple hosts on the same combined graph dashlet
graph_info["used_space"] = {
    "title": _("Used storage space"),
    "metrics": [
        ("used_space", "line"),
    ],
}

graph_info["io_flow"] = {
    "title": "IO flow",
    "metrics": [
        ("egress", "-area"),
        ("ingress", "area"),
    ],
}
