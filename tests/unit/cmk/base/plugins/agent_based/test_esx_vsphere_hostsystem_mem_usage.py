#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import OrderedDict

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.esx_vsphere_hostsystem_mem_usage import (
    check_esx_vsphere_hostsystem_mem_usage,
    cluster_check_esx_vsphere_hostsystem_mem_usage,
    discover_esx_vsphere_hostsystem_mem_usage,
)


@pytest.mark.parametrize(
    "section, discovered_service",
    [
        (
            OrderedDict(
                [
                    ("summary.quickStats.overallMemoryUsage", ["73317"]),
                    ("hardware.memorySize", ["206121951232"]),
                ]
            ),
            [Service()],
        ),
        (
            OrderedDict(
                [
                    ("summary.quickStats.overallMemoryUsage", ["73317"]),
                ]
            ),
            [],
        ),
    ],
)
def test_discover_esx_vsphere_hostsystem_mem_usage(section, discovered_service) -> None:
    assert list(discover_esx_vsphere_hostsystem_mem_usage(section)) == discovered_service


@pytest.mark.parametrize(
    "section, check_results",
    [
        (
            OrderedDict(
                [
                    ("summary.quickStats.overallMemoryUsage", ["73317"]),
                    ("hardware.memorySize", ["206121951232"]),
                ]
            ),
            [
                Result(state=State.OK, summary="Usage: 37.30% - 71.6 GiB of 192 GiB"),
                Metric(
                    "mem_used",
                    76878446592.0,
                    levels=(164897560985.6, 185509756108.80002),
                    boundaries=(0.0, 206121951232.0),
                ),
                Metric("mem_total", 206121951232.0),
            ],
        ),
        (
            OrderedDict(
                [
                    ("summary.quickStats.overallMemoryUsage", ["73317"]),
                ]
            ),
            [],
        ),
        (
            OrderedDict(
                [
                    ("summary.quickStats.overallMemoryUsage", ["73317"]),
                    ("hardware.memorySize", ["broken"]),
                ]
            ),
            [],
        ),
        (
            OrderedDict(
                [
                    ("summary.quickStats.overallMemoryUsage", ["73317"]),
                    ("hardware.memorySize", []),
                ]
            ),
            [],
        ),
    ],
)
def test_check_esx_vsphere_hostsystem_mem_usage(section, check_results) -> None:
    assert (
        list(
            check_esx_vsphere_hostsystem_mem_usage(
                {"levels_upper": (80.0, 90.0)},
                section,
            )
        )
        == check_results
    )


@pytest.mark.parametrize(
    "section, params, check_results",
    [
        (
            {
                "nodebert": OrderedDict(
                    [
                        ("summary.quickStats.overallMemoryUsage", ["73317"]),
                        ("hardware.memorySize", ["206121951232"]),
                    ]
                ),
                "nodette": OrderedDict(
                    [
                        ("summary.quickStats.overallMemoryUsage", ["28304"]),
                        ("hardware.memorySize", ["637495773339"]),
                    ]
                ),
            },
            {
                "levels_upper": (80.0, 90.0),
            },
            [
                Result(state=State.OK, summary="2 nodes"),
                Result(state=State.OK, summary="Usage: 12.63% - 99.2 GiB of 786 GiB"),
                Metric(
                    "mem_used",
                    106557341696.0,
                    levels=(674894179656.8, 759255952113.9),
                    boundaries=(0.0, 843617724571.0),
                ),
                Metric("mem_total", 843617724571.0),
            ],
        ),
        (
            {
                "nodebert": OrderedDict(
                    [
                        ("summary.quickStats.overallMemoryUsage", ["73317"]),
                        ("hardware.memorySize", ["206121951232"]),
                    ]
                ),
                "nodette": OrderedDict(
                    [
                        ("summary.quickStats.overallMemoryUsage", ["28304"]),
                        ("hardware.memorySize", ["637495773339"]),
                    ]
                ),
            },
            {
                "levels_upper": (80.0, 90.0),
                "cluster": [
                    (
                        1,
                        {
                            "levels_upper": (99.0, 100.0),
                        },
                    ),
                    (
                        3,
                        {
                            "levels_upper": (1.0, 2.0),
                        },
                    ),
                ],
            },
            [
                Result(state=State.OK, summary="2 nodes"),
                Result(state=State.OK, summary="Usage: 12.63% - 99.2 GiB of 786 GiB"),
                Metric(
                    "mem_used",
                    106557341696.0,
                    levels=(835181547325.29, 843617724571.0),
                    boundaries=(0.0, 843617724571.0),
                ),
                Metric("mem_total", 843617724571.0),
            ],
        ),
        (
            {
                "nodebert": OrderedDict(
                    [
                        ("summary.quickStats.overallMemoryUsage", ["73317"]),
                        ("hardware.memorySize", ["206121951232"]),
                    ]
                ),
                "nodette": OrderedDict(
                    [
                        ("summary.quickStats.overallMemoryUsage", ["28304"]),
                        ("hardware.memorySize", ["637495773339"]),
                    ]
                ),
            },
            {
                "levels_upper": (80.0, 90.0),
                "cluster": [
                    (
                        1,
                        {
                            "levels_upper": (99.0, 100.0),
                        },
                    ),
                    (
                        2,
                        {
                            "levels_upper": (1.0, 2.0),
                        },
                    ),
                ],
            },
            [
                Result(state=State.OK, summary="2 nodes"),
                Result(
                    state=State.CRIT,
                    summary="Usage: 12.63% - 99.2 GiB of 786 GiB (warn/crit at 1.00%/2.00% used)",
                ),
                Metric(
                    "mem_used",
                    106557341696.0,
                    levels=(8436177245.71, 16872354491.42),
                    boundaries=(0.0, 843617724571.0),
                ),
                Metric("mem_total", 843617724571.0),
            ],
        ),
        (
            {
                "nodebert": OrderedDict(
                    [
                        ("summary.quickStats.overallMemoryUsage", ["73317"]),
                        ("hardware.memorySize", ["206121951232"]),
                    ]
                ),
                "nodette": OrderedDict(
                    [
                        ("summary.quickStats.overallMemoryUsage", ["28304"]),
                    ]
                ),
            },
            {
                "levels_upper": (80.0, 90.0),
            },
            [
                Result(state=State.OK, summary="2 nodes"),
                Result(state=State.OK, summary="Usage: 37.30% - 71.6 GiB of 192 GiB"),
                Metric(
                    "mem_used",
                    76878446592.0,
                    levels=(164897560985.6, 185509756108.80002),
                    boundaries=(0.0, 206121951232.0),
                ),
                Metric("mem_total", 206121951232.0),
            ],
        ),
        (
            {
                "nodebert": OrderedDict(
                    [
                        ("summary.quickStats.overallMemoryUsage", ["bla"]),
                        ("hardware.memorySize", ["206121951232"]),
                    ]
                ),
                "nodette": OrderedDict(
                    [
                        ("summary.quickStats.overallMemoryUsage", ["28304"]),
                        ("hardware.memorySize", ["637495773339"]),
                    ]
                ),
            },
            {
                "levels_upper": (80.0, 90.0),
            },
            [
                Result(state=State.OK, summary="2 nodes"),
                Result(state=State.OK, summary="Usage: 4.66% - 27.6 GiB of 594 GiB"),
                Metric(
                    "mem_used",
                    29678895104.0,
                    levels=(509996618671.2, 573746196005.1),
                    boundaries=(0.0, 637495773339.0),
                ),
                Metric("mem_total", 637495773339.0),
            ],
        ),
        (
            {
                "nodebert": OrderedDict(
                    [
                        ("summary.quickStats.overallMemoryUsage", ["73317"]),
                        ("hardware.memorySize", ["206121951232"]),
                    ]
                ),
                "nodette": None,
            },
            {
                "levels_upper": (80.0, 90.0),
            },
            [
                Result(state=State.OK, summary="2 nodes"),
                Result(state=State.OK, summary="Usage: 37.30% - 71.6 GiB of 192 GiB"),
                Metric(
                    "mem_used",
                    76878446592.0,
                    levels=(164897560985.6, 185509756108.80002),
                    boundaries=(0.0, 206121951232.0),
                ),
                Metric("mem_total", 206121951232.0),
            ],
        ),
        (
            {
                "nodebert": None,
                "nodette": None,
            },
            {
                "levels_upper": (80.0, 90.0),
            },
            [],
        ),
    ],
)
def test_cluster_check_esx_vsphere_hostsystem_mem_usage(section, params, check_results) -> None:
    assert (
        list(
            cluster_check_esx_vsphere_hostsystem_mem_usage(
                params,
                section,
            )
        )
        == check_results
    )
