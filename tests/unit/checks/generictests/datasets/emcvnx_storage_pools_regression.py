#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "emcvnx_storage_pools"

parsed = {
    "backup": {
        "Disk Type": "Mixed",
        "Relocation Type": "Scheduled",
        "Performance_User Capacity (GBs)": "4400.83",
        "Deduplicated LUNs' Tiering Policy": "Auto Tier",
        "Compression Savings (GBs)": "N/A",
        "Raw Capacity (GBs)": "20177.924",
        "Capacity_Consumed Capacity (GBs)": "9096.98",
        "Efficiency Savings (Blocks)": "N/A",
        "Deduplication Status": "OK(0x0)",
        "Current Operation State": "N/A",
        "Deduplication Remaining Size (GBs)": "N/A",
        "Deduplication Percent Completed": "-42",
        "Performance_Data Targeted for Higher Tier (GBs)": "0.00",
        "Consumed Capacity (GBs)": "13058.455",
        "Current Operation Percent Completed": "0",
        "tier_names": ["Performance", "Capacity"],
        "Rebalance Percent Complete": "N/A",
        "Deduplicated LUNs' Initial Tier": "Highest Available",
        "Deduplication Remaining Size (Blocks)": "N/A",
        "Snapshot Subscribed Capacity (GBs)": "0.000",
        "FAST Cache": "Disabled",
        "Percent Full": "84.763",
        "User Capacity (GBs)": "15405.781",
        "Performance_Data Targeted Within Tier (GBs)": "0.00",
        "Deduplication Shared Capacity (Blocks)": "N/A",
        "Deduplication State": "Idle (No Deduplicated LUNs)",
        "Percent Full Threshold": "80",
        "Metadata Subscribed Capacity (GBs)": "433.954",
        "Raw Capacity (Blocks)": "42316172978",
        "Capacity_Data Targeted for Lower Tier (GBs)": "0.00",
        "Schedule Duration Remaining": "None",
        "Total Subscribed Capacity (Blocks)": "27384514560",
        "Data to Move Within Tiers (GBs)": "0.00",
        "State": "Ready",
        "Efficiency Savings (GBs)": "N/A",
        "LUN Allocation (GBs)": "12624.000",
        "Capacity_Raid Drive Count": "8",
        "Available Capacity (GBs)": "2347.326",
        "Data to Move Up (GBs)": "17.03",
        "Available Capacity (Blocks)": "4922698752",
        "Deduplication Shared Capacity (GBs)": "N/A",
        "Auto-Delete Pool Full High Watermark": "95.00",
        "Auto-Tiering": "Scheduled",
        "Auto-Delete Pool Full State": "Idle",
        "Auto-Delete Snapshot Space Used State": "Idle",
        "Compression Savings (Blocks)": "N/A",
        "LUN Allocation (Blocks)": "26474446848",
        "LUN Subscribed Capacity (GBs)": "12624.000",
        "LUNs": "395, 328, 164, 70, 356, 80, 360, 330, 273, 62, 347, 267, 299, 263, 209, 264, 206, 89, 307, 364, 64, 371, 135, 323, 268, 315, 69, 332, 326, 376, 77, 394, 57, 261, 122, 271, 170, 266, 246, 272, 73, 167, 366, 179, 156, 381, 310, 344, 270, 86, 317, 75, 336, 117, 52, 107, 378, 240, 374, 112, 312, 291, 59, 253, 321, 68, 55, 274, 162, 385, 265, 95, 369, 359, 334, 386, 142, 358, 380, 128, 338, 319, 269, 66, 383, 32, 257, 275, 96, 27, 149, 102, 50",
        "Metadata Subscribed Capacity (Blocks)": "910067712",
        "Capacity_Percent Subscribed": "82.66%",
        "Performance_Data Targeted for Lower Tier (GBs)": "17.03",
        "Performance_Raid Type": "r_5",
        "Oversubscribed by (GBs)": "0.000",
        "Deduplication Rate": "Medium",
        "Auto-Delete Pool Full Threshold Enabled": "On",
        "Snapshot Allocation (GBs)": "0.000",
        "Performance_Percent Subscribed": "90.01%",
        "Estimated Time to Complete": "4 minutes",
        "Capacity_Data Targeted for Higher Tier (GBs)": "17.03",
        "Total Subscribed Capacity (GBs)": "13057.954",
        "User Capacity (Blocks)": "32308263936",
        "Auto-Delete Snapshot Space Used Low Watermark": "20.00",
        "Status": "OK(0x0)",
        "Oversubscribed by (Blocks)": "0",
        "Pool ID": "2",
        "Relocation Rate": "Medium",
        "Auto-Delete Pool Full Low Watermark": "85.00",
        "Capacity_Data Targeted Within Tier (GBs)": "0.00",
        "Current Operation Status": "N/A",
        "Relocation Status": "Inactive",
        "Disks": "",
        "Performance_Raid Drive Count": "5",
        "Metadata Allocation (GBs)": "434.455",
        "Metadata Allocation (Blocks)": "911118336",
        "Data to Move Down (GBs)": "17.03",
        "Optimal Deduplicated LUN SP Owner": "N/A",
        "Snapshot Subscribed Capacity (Blocks)": "0",
        "LUN Subscribed Capacity (Blocks)": "26474446848",
        "Current Operation": "None",
        "Description": "",
        "Capacity_Raid Type": "r_6",
        "Performance_Consumed Capacity (GBs)": "3960.97",
        "Snapshot Allocation (Blocks)": "0",
        "Storage Pool ID": "2",
        "Performance_Available Capacity (GBs)": "439.86",
        "Raid Type": "Mixed",
        "Capacity_Available Capacity (GBs)": "1907.97",
        "Consumed Capacity (Blocks)": "27385565184",
        "Capacity_User Capacity (GBs)": "11004.95",
        "Data Movement Completed (GBs)": "102.70",
        "Auto-Delete Snapshot Space Used Threshold Enabled": "Off",
        "Auto-Delete Snapshot Space Used High Watermark": "25.00",
        "Percent Subscribed": "84.760",
    }
}

discovery = {
    "": [("backup", {})],
    "tieringtypes": [("backup Capacity", {}), ("backup Performance", {})],
    "tiering": [("backup", {})],
    "deduplication": [("backup", {})],
}

checks = {
    "": [
        (
            "backup",
            {"percent_full": (70.0, 90.0)},
            [
                (
                    0,
                    "State: Ready, Status: OK(0x0), [Phys. capacity] User capacity: 15.0 TiB, Consumed capacity: 12.8 TiB, Available capacity: 2.29 TiB",
                    [],
                ),
                (1, "Percent full: 84.76% (warn/crit at 70 B/90 B)", []),
                (
                    0,
                    "[Virt. capacity] Percent subscribed: 84.76%, Oversubscribed by: 0 B, Total subscribed capacity: 12.8 TiB",
                    [
                        ("emcvnx_consumed_capacity", 14021409290321.92, None, None, None, None),
                        ("emcvnx_avail_capacity", 2520422100762.624, None, None, None, None),
                        ("emcvnx_perc_full", 84.763, None, None, None, None),
                        ("emcvnx_perc_subscribed", 84.76, None, None, None, None),
                        ("emcvnx_over_subscribed", 0.0, None, None, None, None),
                        (
                            "emcvnx_total_subscribed_capacity",
                            14020871345668.096,
                            None,
                            None,
                            None,
                            None,
                        ),
                    ],
                ),
            ],
        )
    ],
    "tieringtypes": [
        (
            "backup Capacity",
            {},
            [
                (0, "User capacity: 10.7 TiB", []),
                (
                    0,
                    "Consumed capacity: 8.88 TiB",
                    [("emcvnx_consumed_capacity", 9767807898091.52, None, None, None, None)],
                ),
                (
                    0,
                    "Available capacity: 1.86 TiB",
                    [("emcvnx_avail_capacity", 2048667187937.28, None, None, None, None)],
                ),
                (
                    0,
                    "Percent subscribed: 82.66%",
                    [("emcvnx_perc_subscribed", 82.66, None, None, None, None)],
                ),
                (
                    0,
                    "Move higher: 17.0 GiB",
                    [("emcvnx_targeted_higher", 18285823262.72, None, None, None, None)],
                ),
                (0, "Move lower: 0 B", [("emcvnx_targeted_lower", 0.0, None, None, None, None)]),
                (0, "Move within: 0 B", [("emcvnx_targeted_within", 0.0, None, None, None, None)]),
            ],
        ),
        (
            "backup Performance",
            {},
            [
                (0, "User capacity: 4.30 TiB", []),
                (
                    0,
                    "Consumed capacity: 3.87 TiB",
                    [("emcvnx_consumed_capacity", 4253059152609.28, None, None, None, None)],
                ),
                (
                    0,
                    "Available capacity: 440 GiB",
                    [("emcvnx_avail_capacity", 472296078704.64, None, None, None, None)],
                ),
                (
                    0,
                    "Percent subscribed: 90.01%",
                    [("emcvnx_perc_subscribed", 90.01, None, None, None, None)],
                ),
                (0, "Move higher: 0 B", [("emcvnx_targeted_higher", 0.0, None, None, None, None)]),
                (
                    0,
                    "Move lower: 17.0 GiB",
                    [("emcvnx_targeted_lower", 18285823262.72, None, None, None, None)],
                ),
                (0, "Move within: 0 B", [("emcvnx_targeted_within", 0.0, None, None, None, None)]),
            ],
        ),
    ],
    "tiering": [
        (
            "backup",
            {"time_to_complete": (1814400, 2419200)},
            [
                (0, "Fast cache: Disabled", []),
                (0, "Relocation status: Inactive", []),
                (0, "Relocation rate: Medium", []),
                (
                    0,
                    "Move up: 17.0 GiB",
                    [("emcvnx_move_up", 18285823262.72, None, None, None, None)],
                ),
                (
                    0,
                    "Move down: 17.0 GiB",
                    [("emcvnx_move_down", 18285823262.72, None, None, None, None)],
                ),
                (0, "Move within: 0 B", [("emcvnx_move_within", 0.0, None, None, None, None)]),
                (
                    0,
                    "Movement completed: 103 GiB",
                    [("emcvnx_move_completed", 110273285324.8, None, None, None, None)],
                ),
                (0, "Estimated time to complete: 4 minutes", []),
                (
                    0,
                    "Age: 4 minutes 0 seconds",
                    [("emcvnx_time_to_complete", 240, 1814400.0, 2419200.0, None, None)],
                ),
            ],
        )
    ],
    "deduplication": [
        (
            "backup",
            {},
            [
                (0, "State: Idle (No Deduplicated LUNs)", []),
                (0, "Status: OK", []),
                (0, "Rate: Medium", []),
                (0, "Efficiency savings: N/A", []),
                (
                    0,
                    "Percent completed: -42.00%",
                    [("emcvnx_dedupl_perc_completed", -42.0, None, None, None, None)],
                ),
                (0, "Remaining size: N/A", []),
                (0, "Shared capacity: N/A", []),
            ],
        )
    ],
}
