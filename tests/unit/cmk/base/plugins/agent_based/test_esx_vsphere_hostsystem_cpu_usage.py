#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import OrderedDict

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.esx_vsphere_hostsystem_cpu_usage import (
    check_esx_vsphere_hostsystem_cpu_usage,
    cluster_check_esx_vsphere_hostsystem_cpu_usage,
    discover_esx_vsphere_hostsystem_cpu_usage,
    EsxVsphereHostsystemCpuSection,
    extract_esx_vsphere_hostsystem_cpu_usage,
)


@pytest.mark.parametrize(
    "section, cpu_section",
    [
        (
            OrderedDict(
                [
                    ("hardware.cpuInfo.hz", ["2199999833"]),
                    ("hardware.cpuInfo.numCpuCores", ["20"]),
                    ("hardware.cpuInfo.numCpuPackages", ["2"]),
                    ("hardware.cpuInfo.numCpuThreads", ["40"]),
                    ("summary.quickStats.overallCpuUsage", ["3977"]),
                ]
            ),
            EsxVsphereHostsystemCpuSection(
                num_sockets=2,
                num_cores=20,
                num_threads=40,
                used_mhz=3977.0,
                mhz_per_core=2199999833.0,
            ),
        ),
        (
            OrderedDict(
                [
                    ("hardware.cpuInfo.hz", ["2199999833"]),
                    ("hardware.cpuInfo.numCpuCores", ["20"]),
                    ("hardware.cpuInfo.numCpuPackages", ["2"]),
                    ("hardware.cpuInfo.numCpuThreads", ["40"]),
                ]
            ),
            None,
        ),
    ],
)
def test_extract_esx_vsphere_hostsystem_cpu(section, cpu_section) -> None:
    assert extract_esx_vsphere_hostsystem_cpu_usage(section) == cpu_section


@pytest.mark.parametrize(
    "section, discovered_service",
    [
        (
            OrderedDict(
                [
                    ("hardware.cpuInfo.hz", ["2199999833"]),
                    ("hardware.cpuInfo.numCpuCores", ["20"]),
                    ("hardware.cpuInfo.numCpuPackages", ["2"]),
                    ("hardware.cpuInfo.numCpuThreads", ["40"]),
                    ("summary.quickStats.overallCpuUsage", ["3977"]),
                ]
            ),
            [Service()],
        ),
        (
            OrderedDict(
                [
                    ("hardware.cpuInfo.hz", ["2199999833"]),
                    ("hardware.cpuInfo.numCpuCores", ["20"]),
                    ("hardware.cpuInfo.numCpuPackages", ["2"]),
                    ("hardware.cpuInfo.numCpuThreads", ["40"]),
                ]
            ),
            [],
        ),
    ],
)
def test_discover_esx_vsphere_hostsystem_cpu_usage(section, discovered_service) -> None:
    assert list(discover_esx_vsphere_hostsystem_cpu_usage(section, None)) == discovered_service


@pytest.mark.parametrize(
    "section, params, check_results",
    [
        (
            OrderedDict(
                [
                    ("hardware.cpuInfo.hz", ["2199999833"]),
                    ("hardware.cpuInfo.numCpuCores", ["20"]),
                    ("hardware.cpuInfo.numCpuPackages", ["2"]),
                    ("hardware.cpuInfo.numCpuThreads", ["40"]),
                    ("summary.quickStats.overallCpuUsage", ["3977"]),
                ]
            ),
            {},
            [
                Result(state=State.OK, summary="Total CPU: 9.04%"),
                Metric("util", 9.038637049751086, boundaries=(0.0, None)),
                Result(state=State.OK, notice="3.98 GHz/44.0 GHz"),
                Result(state=State.OK, notice="Sockets: 2"),
                Result(state=State.OK, notice="Cores/socket: 10"),
                Result(state=State.OK, notice="Threads: 40"),
            ],
        ),
        (
            OrderedDict(
                [
                    ("hardware.cpuInfo.hz", ["2199999833"]),
                    ("hardware.cpuInfo.numCpuCores", ["20"]),
                    ("hardware.cpuInfo.numCpuPackages", ["2"]),
                    ("hardware.cpuInfo.numCpuThreads", ["40"]),
                    ("summary.quickStats.overallCpuUsage", ["3977"]),
                ]
            ),
            {
                "cluster": [
                    (
                        1,
                        {"util": (3.0, 5.0)},
                    ),
                ],
            },
            [
                Result(state=State.OK, summary="Total CPU: 9.04%"),
                Metric("util", 9.038637049751086, boundaries=(0.0, None)),
                Result(state=State.OK, notice="3.98 GHz/44.0 GHz"),
                Result(state=State.OK, notice="Sockets: 2"),
                Result(state=State.OK, notice="Cores/socket: 10"),
                Result(state=State.OK, notice="Threads: 40"),
            ],
        ),
    ],
)
def test_check_esx_vsphere_hostsystem_cpu(section, params, check_results) -> None:
    assert list(check_esx_vsphere_hostsystem_cpu_usage(params, section, None)) == check_results


@pytest.mark.parametrize(
    "section, params, check_results",
    [
        (
            {
                "nodebert": OrderedDict(
                    [
                        ("hardware.cpuInfo.hz", ["2199999833"]),
                        ("hardware.cpuInfo.numCpuCores", ["20"]),
                        ("hardware.cpuInfo.numCpuPackages", ["2"]),
                        ("hardware.cpuInfo.numCpuThreads", ["40"]),
                        ("summary.quickStats.overallCpuUsage", ["3977"]),
                    ]
                ),
                "nodette": OrderedDict(
                    [
                        ("hardware.cpuInfo.hz", ["2199999776"]),
                        ("hardware.cpuInfo.numCpuCores", ["20"]),
                        ("hardware.cpuInfo.numCpuPackages", ["2"]),
                        ("hardware.cpuInfo.numCpuThreads", ["40"]),
                        ("summary.quickStats.overallCpuUsage", ["531"]),
                    ]
                ),
            },
            {},
            [
                Result(state=State.OK, summary="2 nodes"),
                Result(state=State.OK, summary="Total CPU: 5.12%"),
                Metric("util", 5.122727727951486, boundaries=(0.0, None)),
                Result(state=State.OK, notice="4.51 GHz/88.0 GHz"),
                Result(state=State.OK, notice="Sockets: 4"),
                Result(state=State.OK, notice="Cores/socket: 10"),
                Result(state=State.OK, notice="Threads: 80"),
            ],
        ),
        (
            {
                "nodebert": OrderedDict(
                    [
                        ("hardware.cpuInfo.hz", ["2199999833"]),
                        ("hardware.cpuInfo.numCpuCores", ["20"]),
                        ("hardware.cpuInfo.numCpuPackages", ["2"]),
                        ("hardware.cpuInfo.numCpuThreads", ["40"]),
                        ("summary.quickStats.overallCpuUsage", ["3977"]),
                    ]
                ),
                "nodette": OrderedDict(
                    [
                        ("hardware.cpuInfo.hz", ["2199999776"]),
                        ("hardware.cpuInfo.numCpuCores", ["20"]),
                        ("hardware.cpuInfo.numCpuPackages", ["2"]),
                        ("hardware.cpuInfo.numCpuThreads", ["40"]),
                        ("summary.quickStats.overallCpuUsage", ["531"]),
                    ]
                ),
            },
            {
                "cluster": [
                    (
                        1,
                        {"util": (3.0, 5.0)},
                    ),
                    (
                        3,
                        {"util": (90.0, 95.0)},
                    ),
                ],
            },
            [
                Result(state=State.OK, summary="2 nodes"),
                Result(state=State.CRIT, summary="Total CPU: 5.12% (warn/crit at 3.00%/5.00%)"),
                Metric("util", 5.122727727951486, levels=(3.0, 5.0), boundaries=(0.0, None)),
                Result(state=State.OK, notice="4.51 GHz/88.0 GHz"),
                Result(state=State.OK, notice="Sockets: 4"),
                Result(state=State.OK, notice="Cores/socket: 10"),
                Result(state=State.OK, notice="Threads: 80"),
            ],
        ),
        (
            {
                "nodebert": OrderedDict(
                    [
                        ("hardware.cpuInfo.hz", ["2199999833"]),
                        ("hardware.cpuInfo.numCpuCores", ["20"]),
                        ("hardware.cpuInfo.numCpuPackages", ["2"]),
                        ("hardware.cpuInfo.numCpuThreads", ["40"]),
                        ("summary.quickStats.overallCpuUsage", ["3977"]),
                    ]
                ),
                "nodette": OrderedDict(
                    [
                        ("hardware.cpuInfo.hz", ["2199999776"]),
                        ("hardware.cpuInfo.numCpuCores", ["20"]),
                        ("hardware.cpuInfo.numCpuPackages", ["2"]),
                        ("hardware.cpuInfo.numCpuThreads", ["40"]),
                        ("summary.quickStats.overallCpuUsage", ["531"]),
                    ]
                ),
            },
            {"util": (3.0, 5.0)},
            [
                Result(state=State.OK, summary="2 nodes"),
                Result(state=State.CRIT, summary="Total CPU: 5.12% (warn/crit at 3.00%/5.00%)"),
                Metric("util", 5.122727727951486, levels=(3.0, 5.0), boundaries=(0.0, None)),
                Result(state=State.OK, notice="4.51 GHz/88.0 GHz"),
                Result(state=State.OK, notice="Sockets: 4"),
                Result(state=State.OK, notice="Cores/socket: 10"),
                Result(state=State.OK, notice="Threads: 80"),
            ],
        ),
        (
            {
                "nodebert": OrderedDict(
                    [
                        ("hardware.cpuInfo.hz", ["2199999833"]),
                        ("hardware.cpuInfo.numCpuCores", ["20"]),
                        ("hardware.cpuInfo.numCpuPackages", ["2"]),
                        ("hardware.cpuInfo.numCpuThreads", ["40"]),
                        ("summary.quickStats.overallCpuUsage", ["3977"]),
                    ]
                ),
                "nodette": None,
            },
            {},
            [
                Result(state=State.OK, summary="2 nodes"),
                Result(state=State.OK, summary="Total CPU: 9.04%"),
                Metric("util", 9.038637049751086, boundaries=(0.0, None)),
                Result(state=State.OK, notice="3.98 GHz/44.0 GHz"),
                Result(state=State.OK, notice="Sockets: 2"),
                Result(state=State.OK, notice="Cores/socket: 10"),
                Result(state=State.OK, notice="Threads: 40"),
            ],
        ),
        (
            {
                "nodebert": None,
                "nodette": None,
            },
            {},
            [],
        ),
    ],
)
def test_cluster_check_esx_vsphere_hostsystem_cpu(section, params, check_results) -> None:
    assert (
        list(
            cluster_check_esx_vsphere_hostsystem_cpu_usage(
                params,
                section,
                {
                    "nodebert": None,
                    "nodette": None,
                },
            )
        )
        == check_results
    )
