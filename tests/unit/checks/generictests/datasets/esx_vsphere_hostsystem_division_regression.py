#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore

from cmk.base.plugins.agent_based.esx_vsphere_hostsystem_section import parse_esx_vsphere_hostsystem

checkname = "esx_vsphere_hostsystem"


parsed = parse_esx_vsphere_hostsystem(
    [
        [
            "config.multipathState.path",
            "fc.2000001b329d47ad:2100001b329d47ad-fc.207000c0ffd76501:207000c0ffd76501-naa.600c0ff000d775af138c0a5601000000",
            "active",
            "fc.2000001b329d47ad:2100001b329d47ad-fc.207800c0ffd76501:217800c0ffd76501-naa.600c0ff000d7ba43d28c0a5601000000",
            "active",
            "fc.2001001b32bd47ad:2101001b32bd47ad-fc.207000c0ffd765cf:207000c0ffd765cf-naa.600c0ff000d77506480f3a5601000000",
            "active",
            "fc.2001001b32bd47ad:2101001b32bd47ad-fc.207000c0ffd765cf:207000c0ffd765cf-naa.600c0ff000d775066e113a5601000000",
            "active",
            "fc.2001001b32bd47ad:2101001b32bd47ad-fc.207800c0ffd765cf:217800c0ffd765cf-naa.600c0ff000d7bbd91d113a5601000000",
            "active",
            "sas.5005076b02c2618c-sas.626b411b9f799080-naa.50024e9201d0794b",
            "active",
        ],
        ["hardware.biosInfo.biosVersion", "-[MJE140BUS-1.18]-"],
        ["hardware.biosInfo.releaseDate", "2011-04-04T00:00:00Z"],
        ["hardware.cpuInfo.hz", "2500088448"],
        ["hardware.cpuInfo.numCpuCores", "8"],
        ["hardware.cpuInfo.numCpuPackages", "2"],
        ["hardware.cpuInfo.numCpuThreads", "8"],
        ["hardware.cpuPkg.busHz.0", "333345084"],
        ["hardware.cpuPkg.busHz.1", "333345066"],
        ["hardware.cpuPkg.description.0", "Intel(R)", "Xeon(R)", "CPU", "E5420", "@", "2.50GHz"],
        ["hardware.cpuPkg.description.1", "Intel(R)", "Xeon(R)", "CPU", "E5420", "@", "2.50GHz"],
        ["hardware.cpuPkg.hz.0", "2500088331"],
        ["hardware.cpuPkg.hz.1", "2500088566"],
        ["hardware.cpuPkg.index.0", "0"],
        ["hardware.cpuPkg.index.1", "1"],
        ["hardware.cpuPkg.vendor.0", "intel"],
        ["hardware.cpuPkg.vendor.1", "intel"],
        ["hardware.memorySize", "67913404416"],
        ["hardware.systemInfo.model", "IBM", "eServer", "BladeCenter", "HS21", "-[7995G3G]-"],
        ["hardware.systemInfo.otherIdentifyingInfo.AssetTag.0", "unknown"],
        [
            "hardware.systemInfo.otherIdentifyingInfo.OemSpecificString.0",
            "IBM",
            "BaseBoard",
            "Management",
            "Controller",
            "-[MJBT34A",
            "]-",
        ],
        [
            "hardware.systemInfo.otherIdentifyingInfo.OemSpecificString.1",
            "IBM",
            "Diagnostics",
            "-[MJYT20AUS]-",
        ],
        [
            "hardware.systemInfo.otherIdentifyingInfo.ServiceTag.0",
            "-[UUID:2DDCB758CE5611DD94EF00145EE1FCDA]-",
        ],
        ["hardware.systemInfo.otherIdentifyingInfo.ServiceTag.1", "99C8785"],
        ["hardware.systemInfo.uuid", "c05d99a8-1861-b601-6927-001a645a8f28"],
        ["hardware.systemInfo.vendor", "IBM"],
        ["name", "srvesxblade06.comline.de"],
        ["overallStatus", "green"],
        ["runtime.inMaintenanceMode", "false"],
        ["runtime.powerState", "poweredOn"],
        ["summary.quickStats.overallCpuUsage", "10733"],
        ["summary.quickStats.overallMemoryUsage", "53325"],
    ]
)


discovery = {
    "": [],
    "cpu_usage": [(None, {})],
    "cpu_util_cluster": [],
    "maintenance": [(None, {"target_state": "false"})],
    "mem_usage": [(None, "esx_host_mem_default_levels")],
    "mem_usage_cluster": [],
    "multipath": [],
    "state": [(None, None)],
}


checks = {
    "cpu_usage": [
        (
            None,
            {},
            [
                (0, "Total CPU: 53.66%", [("util", 53.66310144240145, None, None, 0, 100)]),
                (0, "10.73GHz/20.00GHz", []),
                (0, "2 sockets, 4 cores/socket, 8 threads", []),
            ],
        )
    ],
    "maintenance": [(None, {"target_state": "false"}, [(0, "System not in Maintenance mode", [])])],
    "mem_usage": [
        (
            None,
            (80.0, 90.0),
            [
                (
                    1,
                    "Usage: 82.33% - 52.1 GiB of 63.3 GiB (warn/crit at 80.00%/90.00% used)",
                    [
                        ("mem_used", 55915315200.0, 54330723532.8, 61122063974.4, 0, 67913404416.0),
                        ("mem_total", 67913404416.0, None, None, None, None),
                    ],
                )
            ],
        )
    ],
    "state": [(None, {}, [(0, "Entity state: green", []), (0, "Power state: poweredOn", [])])],
}
