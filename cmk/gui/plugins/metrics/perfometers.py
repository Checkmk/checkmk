#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing import perfometer_info
from cmk.gui.graphing._utils import GB, MAX_NUMBER_HOPS, MB, TB

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
        "type": "logarithmic",
        "metric": "runtime",
        "half_value": 864000.0,
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
        "metric": "connector_outlets",
        "half_value": 20,
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
    {"type": "logarithmic", "metric": "temp", "half_value": 40.0, "exponent": 1.2}
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
        "type": "logarithmic",
        "metric": "database_size",
        "half_value": GB,
        "exponent": 5.0,
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
        "type": "logarithmic",
        "metric": "connections",
        "half_value": 50,
        "exponent": 2,
    }
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
                "metric": "net_data_recv",
                "half_value": 5000000,
                "exponent": 5,
            },
            {
                "type": "logarithmic",
                "metric": "net_data_sent",
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
    {
        "type": "linear",
        "segments": ["tablespace_used"],
        "total": "tablespace_max_size",
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
        "type": "linear",
        "segments": ["cache_hit_ratio"],
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
        "type": "linear",
        "segments": ["tapes_util"],
        "total": 100.0,
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
        "metric": "shared_memory_segments",
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
        "type": "linear",
        "segments": ["read_hits"],
        "total": 100.0,
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
        "type": "linear",
        "segments": ["io_consumption_percent"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "dual",
        "perfometers": [
            {
                "type": "logarithmic",
                "metric": "ingress",
                "half_value": GB,
                "exponent": 3,
            },
            {
                "type": "logarithmic",
                "metric": "egress",
                "half_value": GB,
                "exponent": 3,
            },
        ],
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["snat_usage"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "logarithmic",
        "metric": "queries_per_sec",
        "half_value": 1000,
        "exponent": 2,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["cpu_reservation"],
        "total": 100.0,
    }
)
