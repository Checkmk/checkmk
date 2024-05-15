#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code=var-annotated


checkname = "ibm_svc_nodestats"


info = [
    ["1", "BLUBBSVC01", "compression_cpu_pc", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "cpu_pc", "1", "3", "140325134526"],
    ["1", "BLUBBSVC01", "fc_mb", "35", "530", "140325134526"],
    ["1", "BLUBBSVC01", "fc_io", "5985", "11194", "140325134751"],
    ["1", "BLUBBSVC01", "sas_mb", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "sas_io", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "iscsi_mb", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "iscsi_io", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "write_cache_pc", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "total_cache_pc", "70", "77", "140325134716"],
    ["1", "BLUBBSVC01", "vdisk_mb", "1", "246", "140325134526"],
    ["1", "BLUBBSVC01", "vdisk_io", "130", "1219", "140325134501"],
    ["1", "BLUBBSVC01", "vdisk_ms", "0", "4", "140325134531"],
    ["1", "BLUBBSVC01", "mdisk_mb", "17", "274", "140325134526"],
    ["1", "BLUBBSVC01", "mdisk_io", "880", "1969", "140325134526"],
    ["1", "BLUBBSVC01", "mdisk_ms", "1", "5", "140325134811"],
    ["1", "BLUBBSVC01", "drive_mb", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "drive_io", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "drive_ms", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "vdisk_r_mb", "0", "244", "140325134526"],
    ["1", "BLUBBSVC01", "vdisk_r_io", "19", "1022", "140325134501"],
    ["1", "BLUBBSVC01", "vdisk_r_ms", "2", "8", "140325134756"],
    ["1", "BLUBBSVC01", "vdisk_w_mb", "0", "2", "140325134701"],
    ["1", "BLUBBSVC01", "vdisk_w_io", "110", "210", "140325134901"],
    ["1", "BLUBBSVC01", "vdisk_w_ms", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "mdisk_r_mb", "1", "265", "140325134526"],
    ["1", "BLUBBSVC01", "mdisk_r_io", "15", "1081", "140325134526"],
    ["1", "BLUBBSVC01", "mdisk_r_ms", "5", "23", "140325134616"],
    ["1", "BLUBBSVC01", "mdisk_w_mb", "16", "132", "140325134751"],
    ["1", "BLUBBSVC01", "mdisk_w_io", "865", "1662", "140325134736"],
    ["1", "BLUBBSVC01", "mdisk_w_ms", "1", "5", "140325134811"],
    ["1", "BLUBBSVC01", "drive_r_mb", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "drive_r_io", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "drive_r_ms", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "drive_w_mb", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "drive_w_io", "0", "0", "140325134931"],
    ["1", "BLUBBSVC01", "drive_w_ms", "0", "0", "140325134931"],
    ["5", "BLUBBSVC02", "compression_cpu_pc", "0", "0", "140325134930"],
    ["5", "BLUBBSVC02", "cpu_pc", "1", "2", "140325134905"],
    ["5", "BLUBBSVC02", "fc_mb", "141", "293", "140325134755"],
    ["5", "BLUBBSVC02", "fc_io", "7469", "12230", "140325134750"],
    ["5", "BLUBBSVC02", "sas_mb", "0", "0", "140325134930"],
    ["5", "BLUBBSVC02", "sas_io", "0", "0", "140325134930"],
]


discovery = {
    "cache": [("BLUBBSVC01", None)],
    "cpu_util": [
        ("BLUBBSVC01", {}),
        ("BLUBBSVC02", {}),
    ],
    "disk_latency": [
        ("Drives BLUBBSVC01", None),
        ("MDisks BLUBBSVC01", None),
        ("VDisks BLUBBSVC01", None),
    ],
    "diskio": [
        ("Drives BLUBBSVC01", None),
        ("MDisks BLUBBSVC01", None),
        ("VDisks BLUBBSVC01", None),
    ],
    "iops": [("Drives BLUBBSVC01", None), ("MDisks BLUBBSVC01", None), ("VDisks BLUBBSVC01", None)],
}


checks = {
    "cache": [
        (
            "BLUBBSVC01",
            {},
            [
                (
                    0,
                    "Write cache usage is 0 %, total cache usage is 70 %",
                    [
                        ("write_cache_pc", 0, None, None, 0, 100),
                        ("total_cache_pc", 70, None, None, 0, 100),
                    ],
                )
            ],
        )
    ],
    "cpu_util": [
        (
            "BLUBBSVC01",
            {"levels": (90.0, 95.0)},
            [(0, "Total CPU: 1.00%", [("util", 1, 90.0, 95.0, 0, 100)])],
        ),
        (
            "BLUBBSVC02",
            {"levels": (90.0, 95.0)},
            [(0, "Total CPU: 1.00%", [("util", 1, 90.0, 95.0, 0, 100)])],
        ),
    ],
    "disk_latency": [
        (
            "Drives BLUBBSVC01",
            {},
            [
                (
                    0,
                    "Latency is 0.0 ms for read, 0.0 ms for write",
                    [
                        ("read_latency", 0.0, None, None, None, None),
                        ("write_latency", 0.0, None, None, None, None),
                    ],
                )
            ],
        ),
        (
            "MDisks BLUBBSVC01",
            {},
            [
                (
                    0,
                    "Latency is 5.0 ms for read, 1.0 ms for write",
                    [
                        ("read_latency", 5.0, None, None, None, None),
                        ("write_latency", 1.0, None, None, None, None),
                    ],
                )
            ],
        ),
        (
            "VDisks BLUBBSVC01",
            {},
            [
                (
                    0,
                    "Latency is 2.0 ms for read, 0.0 ms for write",
                    [
                        ("read_latency", 2.0, None, None, None, None),
                        ("write_latency", 0.0, None, None, None, None),
                    ],
                )
            ],
        ),
    ],
    "diskio": [
        (
            "Drives BLUBBSVC01",
            {},
            [
                (
                    0,
                    "0.00 B/s read, 0.00 B/s write",
                    [
                        ("read", 0.0, None, None, None, None),
                        ("write", 0.0, None, None, None, None),
                    ],
                )
            ],
        ),
        (
            "MDisks BLUBBSVC01",
            {},
            [
                (
                    0,
                    "1.05 MB/s read, 16.8 MB/s write",
                    [
                        ("read", 1048576.0, None, None, None, None),
                        ("write", 16777216.0, None, None, None, None),
                    ],
                )
            ],
        ),
        (
            "VDisks BLUBBSVC01",
            {},
            [
                (
                    0,
                    "0.00 B/s read, 0.00 B/s write",
                    [
                        ("read", 0.0, None, None, None, None),
                        ("write", 0.0, None, None, None, None),
                    ],
                )
            ],
        ),
    ],
    "iops": [
        (
            "Drives BLUBBSVC01",
            {},
            [
                (
                    0,
                    "0.0 IO/s read, 0.0 IO/s write",
                    [
                        ("read", 0.0, None, None, None, None),
                        ("write", 0.0, None, None, None, None),
                    ],
                )
            ],
        ),
        (
            "MDisks BLUBBSVC01",
            {},
            [
                (
                    0,
                    "15.0 IO/s read, 865.0 IO/s write",
                    [
                        ("read", 15.0, None, None, None, None),
                        ("write", 865.0, None, None, None, None),
                    ],
                )
            ],
        ),
        (
            "VDisks BLUBBSVC01",
            {},
            [
                (
                    0,
                    "19.0 IO/s read, 110.0 IO/s write",
                    [
                        ("read", 19.0, None, None, None, None),
                        ("write", 110.0, None, None, None, None),
                    ],
                )
            ],
        ),
    ],
}
