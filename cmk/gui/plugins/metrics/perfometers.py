#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing import perfometer_info
from cmk.gui.graphing._utils import GB, MAX_NUMBER_HOPS, MB

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
        "type": "logarithmic",
        "metric": "mails_received_time",
        "half_value": 5,
        "exponent": 3,
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
        "type": "logarithmic",
        "metric": "current",
        "half_value": 10,
        "exponent": 4,
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
        "type": "logarithmic",
        "metric": "days",
        "half_value": 100,
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
        "segments": ["disk_utilization"],
        "total": 100.0,
    }
)

perfometer_info.append(
    {
        "type": "linear",
        "segments": ["cpu_reservation"],
        "total": 100.0,
    }
)
