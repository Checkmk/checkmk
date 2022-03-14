#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.metrics.utils import (
    GB,
    MAX_NUMBER_HOPS,
    MB,
    perfometer_info,
    skype_mobile_devices,
    TB,
)

# .
#   .--Perf-O-Meters-------------------------------------------------------.
#   |  ____            __        ___        __  __      _                  |
#   | |  _ \ ___ _ __ / _|      / _ \      |  \/  | ___| |_ ___ _ __ ___   |
#   | | |_) / _ \ '__| |_ _____| | | |_____| |\/| |/ _ \ __/ _ \ '__/ __|  |
#   | |  __/  __/ |  |  _|_____| |_| |_____| |  | |  __/ ||  __/ |  \__ \  |
#   | |_|   \___|_|  |_|        \___/      |_|  |_|\___|\__\___|_|  |___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Definition of Perf-O-Meters                                         |
#   '----------------------------------------------------------------------'

# If multiple Perf-O-Meters apply, the first applicable Perf-O-Meter in the list will
# be the one appearing in the GUI.

# Types of Perf-O-Meters:
# linear      -> multiple values added from left to right
# logarithmic -> one value in a logarithmic scale
# dual        -> two Perf-O-Meters next to each other, the first one from right to left
# stacked     -> two Perf-O-Meters of type linear, logarithmic or dual, stack vertically
# The label of dual and stacked is taken from the definition of the contained Perf-O-Meters

# Optional keys:
# "sort_group" -> When sorting perfometer the first criteria used is either this optional performeter
#                 group or the perfometer ID. The sort_group can be used to group different perfometers
#                 which show equal data for sorting them together in a single sort domain.

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "active_connections",
        "half_value": 50.0,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "dual",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "tcp_active_sessions",
                "half_value": 4,
                "exponent": 2,
            },
            {
                "type": "logarithmic",
                "metric": "udp_active_sessions",
                "half_value": 4,
                "exponent": 2,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "active_sessions",
        "half_value": 50.0,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "parts_per_million",
        "half_value": 50.0,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["mem_used_percent"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["cpu_mem_used_percent"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["ap_devices_drifted", "ap_devices_not_responding"],
        "total": "ap_devices_total",
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["ap_devices_percent_unhealthy"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {"type": "logarithmic", "metric": "wifi_connection_total", "half_value": 5000, "exponent": 2.0}
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["execution_time"],
        "total": 90.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "session_rate",
        "half_value": 50.0,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "uptime",
        "half_value": 2592000.0,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "age",
        "half_value": 2592000.0,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "runtime",
        "half_value": 864000.0,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "last_updated",
        "half_value": 40.0,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "job_duration",
        "half_value": 120.0,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "response_time",
        "half_value": 10,
        "exponent": 4,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "mails_received_time",
        "half_value": 5,
        "exponent": 3,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["mem_perm_used"],
        "total": "mem_perm_used:max",
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["mem_heap"],
        "total": "mem_heap:max",
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["mem_nonheap"],
        "total": "mem_nonheap:max",
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "pressure",
        "half_value": 0.5,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "pressure_pa",
        "half_value": 10,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "cifs_share_users",
        "half_value": 10,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "connector_outlets",
        "half_value": 20,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "licenses",
        "half_value": 500,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "sync_latency",
        "half_value": 5,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "mail_latency",
        "half_value": 5,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "backup_size",
        "half_value": 150 * GB,
        "exponent": 2.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "fw_connections_active",
        "half_value": 100,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "checkpoint_age",
                "half_value": 86400,
                "exponent": 2,
            },
            {
                "type": "logarithmic",
                "metric": "backup_age",
                "half_value": 86400,
                "exponent": 2,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "backup_age",
        "half_value": 86400,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "read_latency",
                "half_value": 5,
                "exponent": 2,
            },
            {
                "type": "logarithmic",
                "metric": "write_latency",
                "half_value": 5,
                "exponent": 2,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "logswitches_last_hour",
        "half_value": 15,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "oracle_count",
        "half_value": 250,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "database_apply_lag",
        "half_value": 2500,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "processes",
        "half_value": 100,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["total_cache_usage"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "mem_heap",
                "half_value": 100 * MB,
                "exponent": 2,
            },
            {
                "type": "logarithmic",
                "metric": "mem_nonheap",
                "half_value": 100 * MB,
                "exponent": 2,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "linear",
                "segments": ["threads_idle"],
                "total": "threads_idle:max",
            },
            {
                "type": "linear",
                "segments": ["threads_busy"],
                "total": "threads_busy:max",
            },
        ],
    }
)

perfometer_info.append({"type": "logarithmic", "metric": "rta", "half_value": 0.1, "exponent": 4})

perfometer_info.append({"type": "logarithmic", "metric": "rtt", "half_value": 0.1, "exponent": 4})

perfometer_info.append(
    {"type": "logarithmic", "metric": "load1", "half_value": 4.0, "exponent": 2.0}
)

perfometer_info.append(
    {"type": "logarithmic", "metric": "temp", "half_value": 40.0, "exponent": 1.2}
)

perfometer_info.append(
    {"type": "logarithmic", "metric": "major_page_faults", "half_value": 1000.0, "exponent": 2.0}
)

perfometer_info.append(
    {"type": "logarithmic", "metric": "threads", "half_value": 400.0, "exponent": 2.0}
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["user", "system", "idle", "nice"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["user", "system", "idle", "io_wait"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["user", "system", "io_wait"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": [
            "fpga_util",
        ],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": [
            "overall_util",
        ],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": [
            "pci_io_util",
        ],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": [
            "memory_util",
        ],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": [
            "util",
        ],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": [
            "util_numcpu_as_max",
        ],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": [
            "generic_util",
        ],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": [
            "util1",
        ],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["user", "system", "streams"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["citrix_load"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "database_size",
        "half_value": GB,
        "exponent": 5.0,
    }
)

# Filesystem check with over-provisioning
perfometer_info.append(
    {
        "type": "linear",
        "condition": "fs_provisioning(%),100,>",
        "segments": [
            "fs_used(%)",
            "100,fs_used(%),-#e3fff9",
            "fs_provisioning(%),100.0,-#ffc030",
        ],
        "total": "fs_provisioning(%)",
        "label": ("fs_used(%)", "%"),
    }
)

# Filesystem check with provisioning, but not over-provisioning
perfometer_info.append(
    {
        "type": "linear",
        "condition": "fs_provisioning(%),100,<=",
        "segments": [
            "fs_used(%)",
            "fs_provisioning(%),fs_used(%),-#ffc030",
            "100,fs_provisioning(%),fs_used(%),-,-#e3fff9",
        ],
        "total": 100,
        "label": ("fs_used(%)", "%"),
    }
)

# Filesystem check without overcommittment
perfometer_info.append(
    {
        "type": "linear",
        "condition": "fs_used,uncommitted,+,fs_size,<",
        "segments": [
            "fs_used",
            "uncommitted",
            "fs_size,fs_used,-,uncommitted,-#e3fff9",  # free
            "0.1#559090",  # fs_size marker
        ],
        "total": "fs_size",
        "label": ("fs_used(%)", "%"),
    }
)

# Filesystem check with overcommittment
perfometer_info.append(
    {
        "type": "linear",
        "condition": "fs_used,uncommitted,+,fs_size,>=",
        "segments": [
            "fs_used",
            "fs_size,fs_used,-#e3fff9",  # free
            "0.1#559090",  # fs_size marker
            "overprovisioned,fs_size,-#ffa000",  # overcommittment
        ],
        "total": "overprovisioned",
        "label": (
            "fs_used,fs_used,uncommitted,+,/,100,*",  # percent used scaled
            "%",
        ),
    }
)

# Filesystem without over-provisioning
perfometer_info.append(
    {
        "type": "linear",
        "segments": [
            "fs_used(%)",
            "100.0,fs_used(%),-#e3fff9",
        ],
        "total": 100,
        "label": ("fs_used(%)", "%"),
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "dedup_rate",
        "half_value": 30.0,
        "exponent": 1.2,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["mem_used", "swap_used", "caches", "mem_free", "swap_free"],
        "label": ("mem_used,swap_used,+,mem_total,/,100,*", "%"),
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["mem_used"],
        "total": "mem_total",
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["mem_used(%)"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["mem_used"],
        "total": "mem_used:max",
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "mem_used",
        "half_value": GB,
        "exponent": 4.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "time_offset",
        "half_value": 1.0,
        "exponent": 10.0,
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "tablespace_wasted",
                "half_value": 1000000,
                "exponent": 2,
            },
            {
                "type": "logarithmic",
                "metric": "indexspace_wasted",
                "half_value": 1000000,
                "exponent": 2,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["running_sessions"],
        "total": "total_sessions",
    }
)

# TODO total : None?
perfometer_info.append(
    {
        "type": "linear",
        "segments": ["shared_locks", "exclusive_locks"],
        "total": None,
    }
)

perfometer_info.append(
    {"type": "logarithmic", "metric": "connections", "half_value": 50, "exponent": 2}
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "connection_time",
        "half_value": 0.2,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "dual",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "input_signal_power_dbm",
                "half_value": 4,
                "exponent": 2,
            },
            {
                "type": "logarithmic",
                "metric": "output_signal_power_dbm",
                "half_value": 4,
                "exponent": 2,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "dual",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "if_in_bps",
                "half_value": 5000000,
                "exponent": 5,
            },
            {
                "type": "logarithmic",
                "metric": "if_out_bps",
                "half_value": 5000000,
                "exponent": 5,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "dual",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "if_in_octets",
                "half_value": 5000000,
                "exponent": 5,
            },
            {
                "type": "logarithmic",
                "metric": "if_out_octets",
                "half_value": 5000000,
                "exponent": 5,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "dual",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "if_out_unicast_octets,if_out_non_unicast_octets,+",
                "half_value": 5000000,
                "exponent": 5,
            },
            {
                "type": "logarithmic",
                "metric": "if_in_octets",
                "half_value": 5000000,
                "exponent": 5,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "dual",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "read_blocks",
                "half_value": 50000000,
                "exponent": 2,
            },
            {
                "type": "logarithmic",
                "metric": "write_blocks",
                "half_value": 50000000,
                "exponent": 2,
            },
        ],
    }
)

perfometer_info.append(
    {"type": "logarithmic", "metric": "running_sessions", "half_value": 10, "exponent": 2}
)

perfometer_info.append(
    {
        "type": "dual",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "deadlocks",
                "half_value": 50,
                "exponent": 2,
            },
            {
                "type": "logarithmic",
                "metric": "lockwaits",
                "half_value": 50,
                "exponent": 2,
            },
        ],
    }
)

# TODO: max fehlt
perfometer_info.append(
    {
        "type": "linear",
        "segments": ["sort_overflow"],
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["tablespace_used"],
        "total": "tablespace_max_size",
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "dual",
                "perfometers": [
                    {"type": "linear", "label": None, "segments": ["total_hitratio"], "total": 100},
                    {"type": "linear", "label": None, "segments": ["data_hitratio"], "total": 100},
                ],
            },
            {
                "type": "dual",
                "perfometers": [
                    {"type": "linear", "label": None, "segments": ["index_hitratio"], "total": 100},
                    {"type": "linear", "label": None, "segments": ["xda_hitratio"], "total": 100},
                ],
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["output_load"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "power",
        "half_value": 1000,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "current",
        "half_value": 10,
        "exponent": 4,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "voltage",
        "half_value": 220.0,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "energy",
        "half_value": 10000,
        "exponent": 3,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["voltage_percent"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["humidity"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "requests_per_second",
                "half_value": 10,
                "exponent": 5,
            },
            {
                "type": "logarithmic",
                "metric": "busy_workers",
                "half_value": 10,
                "exponent": 2,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["cache_hit_ratio"],
        "total": 100,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["varnish_worker_thread_ratio"],
        "total": 100,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["varnish_backend_success_ratio"],
        "total": 100,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["zfs_l2_hit_ratio"],
        "total": 100,
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "signal_noise",
                "half_value": 50.0,
                "exponent": 2.0,
            },
            {
                "type": "linear",
                "segments": ["codewords_corrected", "codewords_uncorrectable"],
                "total": 1.0,
            },
        ],
    }
)

perfometer_info.append(
    {"type": "logarithmic", "metric": "signal_noise", "half_value": 50.0, "exponent": 2.0}
)  # Fallback if no codewords are available

perfometer_info.append(
    {
        "type": "dual",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "disk_read_throughput",
                "half_value": 5000000,
                "exponent": 10,
            },
            {
                "type": "logarithmic",
                "metric": "disk_write_throughput",
                "half_value": 5000000,
                "exponent": 10,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "disk_ios",
        "half_value": 30,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "disk_capacity",
        "half_value": 25 * TB,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "printer_queue",
        "half_value": 10,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "pages_total",
        "half_value": 60000,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["supply_toner_cyan"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["supply_toner_magenta"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["supply_toner_yellow"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["supply_toner_black"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["supply_toner_other"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["smoke_ppm"],
        "total": 10,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["smoke_perc"],
        "total": 100,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["health_perc"],
        "total": 100,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["deviation_calibration_point"],
        "total": 10,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["deviation_airflow"],
        "total": 10,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "airflow",
        "half_value": 300,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "fluidflow",
        "half_value": 0.2,
        "exponent": 5,
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "direct_io",
                "half_value": 25,
                "exponent": 2,
            },
            {
                "type": "logarithmic",
                "metric": "buffered_io",
                "half_value": 25,
                "exponent": 2,
            },
        ],
    }
)

# TODO: :max should be the default?
perfometer_info.append(
    {
        "type": "linear",
        "segments": ["free_dhcp_leases"],
        "total": "free_dhcp_leases:max",
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "host_check_rate",
                "half_value": 50,
                "exponent": 5,
            },
            {
                "type": "logarithmic",
                "metric": "service_check_rate",
                "half_value": 200,
                "exponent": 5,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "normal_updates",
                "half_value": 10,
                "exponent": 2,
            },
            {
                "type": "logarithmic",
                "metric": "security_updates",
                "half_value": 10,
                "exponent": 2,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "registered_phones",
        "half_value": 50,
        "exponent": 3,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "call_legs",
        "half_value": 10,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "mail_queue_deferred_length",
                "half_value": 10000,
                "exponent": 5,
            },
            {
                "type": "logarithmic",
                "metric": "mail_queue_active_length",
                "half_value": 10000,
                "exponent": 5,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "mail_queue_deferred_length",
        "half_value": 10000,
        "exponent": 5,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "messages_inbound,messages_outbound,+",
        "half_value": 100,
        "exponent": 5,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["tapes_util"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "dual",
        "perfometers": [
            {
                "type": "linear",
                "segments": ["qos_dropped_bytes_rate"],
                "total": "qos_dropped_bytes_rate:max",
            },
            {
                "type": "linear",
                "segments": ["qos_outbound_bytes_rate"],
                "total": "qos_outbound_bytes_rate:max",
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "semaphore_ids",
        "half_value": 50,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "segments",
        "half_value": 10,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "semaphores",
        "half_value": 2500,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "dual",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "fc_rx_bytes",
                "half_value": 30 * MB,
                "exponent": 3,
            },
            {
                "type": "logarithmic",
                "metric": "fc_tx_bytes",
                "half_value": 30 * MB,
                "exponent": 3,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "request_rate",
        "half_value": 100,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "mem_pages_rate",
        "half_value": 5000,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["storage_processor_util"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {"type": "linear", "segments": ["active_vpn_tunnels"], "total": "active_vpn_tunnels:max"}
)


def register_hop_perfometers():
    for x in reversed(range(1, MAX_NUMBER_HOPS)):
        perfometer_info.append(
            {
                "type": "dual",
                "perfometers": [
                    {
                        "type": "linear",
                        "segments": ["hop_%d_pl" % x],
                        "total": 100.0,
                    },
                    {
                        "type": "logarithmic",
                        "metric": "hop_%d_rta" % x,
                        "half_value": 0.1,
                        "exponent": 4,
                    },
                ],
            }
        )


register_hop_perfometers()

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["oracle_db_cpu", "oracle_db_wait_time"],
        "total": "20,oracle_db_time,oracle_db_time,30,/,/,+",
    }
)
perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "dual",
                "perfometers": [
                    {
                        "type": "logarithmic",
                        "metric": "oracle_ios_f_total_s_rb",
                        "half_value": 50.0,
                        "exponent": 2,
                    },
                    {
                        "type": "logarithmic",
                        "metric": "oracle_ios_f_total_s_wb",
                        "half_value": 50.0,
                        "exponent": 2,
                    },
                ],
            },
            {
                "type": "dual",
                "perfometers": [
                    {
                        "type": "logarithmic",
                        "metric": "oracle_ios_f_total_l_rb",
                        "half_value": 50.0,
                        "exponent": 2,
                    },
                    {
                        "type": "logarithmic",
                        "metric": "oracle_ios_f_total_l_wb",
                        "half_value": 50.0,
                        "exponent": 2,
                    },
                ],
            },
        ],
    }
)
perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "dual",
                "perfometers": [
                    {
                        "type": "logarithmic",
                        "metric": "oracle_ios_f_total_s_r",
                        "half_value": 50.0,
                        "exponent": 2,
                    },
                    {
                        "type": "logarithmic",
                        "metric": "oracle_ios_f_total_s_w",
                        "half_value": 50.0,
                        "exponent": 2,
                    },
                ],
            },
            {
                "type": "dual",
                "perfometers": [
                    {
                        "type": "logarithmic",
                        "metric": "oracle_ios_f_total_l_r",
                        "half_value": 50.0,
                        "exponent": 2,
                    },
                    {
                        "type": "logarithmic",
                        "metric": "oracle_ios_f_total_l_w",
                        "half_value": 50.0,
                        "exponent": 2,
                    },
                ],
            },
        ],
    }
)
perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "linear",
                "segments": ["oracle_buffer_hit_ratio"],
                "total": 100.0,
            },
            {
                "type": "linear",
                "segments": ["oracle_library_cache_hit_ratio"],
                "total": 100.0,
            },
        ],
    }
)
perfometer_info.append(
    {
        "type": "dual",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "oracle_wait_class_total#00b0c0",
                "half_value": 50.0,
                "exponent": 2,
            },
            {
                "type": "logarithmic",
                "metric": "oracle_wait_class_total_fg#30e0f0",
                "half_value": 50.0,
                "exponent": 2,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "oracle_sga_size,oracle_pga_total_pga_allocated,+",
        "half_value": 16589934592.0,
        "exponent": 2,
    }
)


def get_skype_mobile_perfometer_segments():
    return ["active_sessions_%s" % device for device, _name, _color in skype_mobile_devices]


perfometer_info.append(
    {
        "type": "linear",
        "segments": get_skype_mobile_perfometer_segments(),
        # there is no limit and no way to determine the max so far for
        # all segments
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["filehandler_perc"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["capacity_perc"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "battery_seconds_remaining",
        "half_value": 1800,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "fan",
        "half_value": 3000,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "emcvnx_consumed_capacity",
        "half_value": 20 * TB,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "emcvnx_dedupl_remaining_size",
        "half_value": 20 * TB,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "emcvnx_move_completed",
        "half_value": 250 * GB,
        "exponent": 3,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["read_hits"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["active_vms"],
        "total": 200,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "days",
        "half_value": 100,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["quarantine"],
        "total": 100,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "total_rate",
        "half_value": 50.0,
        "exponent": 2.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "bypass_rate",
        "half_value": 2.0,
        "exponent": 2.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "fireeye_stat_attachment",
        "half_value": 50.0,
        "exponent": 2.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "messages_in_queue",
        "half_value": 1.0,
        "exponent": 2.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "queue",
        "half_value": 80,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "linear",
                "segments": ["connections_perc_used"],
                "total": 100,
            },
            {
                "type": "linear",
                "segments": ["connections_perc_conn_threads"],
                "total": 100,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "used_space",
        "half_value": GB,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "aws_overall_hosts_health_perc",
        "half_value": 100,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "elapsed_time",
        "half_value": 1.0,
        "exponent": 2.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["license_percentage"],
        "total": 100.0,
        "color": "16/a",
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["license_percentage"],
        "total": 100.0,
        "color": "16/a",
    }
)

perfometer_info.append(
    {
        "type": "stacked",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "elasticsearch_size_rate",
                "half_value": 5000,
                "exponent": 2,
            },
            {
                "type": "logarithmic",
                "metric": "elasticsearch_count_rate",
                "half_value": 10,
                "exponent": 2,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "number_of_pending_tasks_rate",
        "half_value": 10,
        "exponent": 2,
        "unit": "count",
    }
)

perfometer_info.append(
    {
        "type": "dual",
        "perfometers": [
            {
                "type": "linear",
                "segments": ["active_primary_shards"],
                "total": "active_shards",
            },
            {
                "type": "linear",
                "segments": ["active_shards"],
                "total": "active_shards",
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["active_shards_percent_as_number"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": [
            "docker_running_containers",
            "docker_paused_containers",
            "docker_stopped_containers",
        ],
        "total": "docker_all_containers",
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "docker_size",
        "half_value": GB,
        "exponent": 2.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "nimble_read_latency_total",
        "half_value": 10,
        "exponent": 2.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "nimble_write_latency_total",
        "half_value": 10,
        "exponent": 2.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["fragmentation"],
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "items_count",
        "half_value": 1000,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["log_file_utilization"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["disk_utilization"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "kube_cpu_usage",
        "half_value": 0.5,  # no clear guidance was available for chosing these values. If more
        # information becomes available, we will update them.
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "kube_memory_usage",
        "half_value": 512 * MB,  # no clear guidance was available for chosing these values. If more
        # information becomes available, we will update them.
        "exponent": 2,
    }
)
