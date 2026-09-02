#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict
from collections.abc import Callable, Mapping
from typing import get_args, get_type_hints
from unittest.mock import call, MagicMock

import pytest
from pytest_mock import MockerFixture

from cmk.automations.results import (
    AnalyzeServiceRuleMatchesResult,
    GetServicesLabelsResult,
    ServiceDiscoveryPreviewResult,
    SetAutochecksInput,
    SetAutochecksV2Result,
    UpdateHostLabelsResult,
)
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.discovery import CheckPreviewEntry, DiscoverySettings
from cmk.checkengine.plugins import AutocheckEntry, CheckPluginName, SectionName
from cmk.gui.openapi.api_endpoints.service_discovery._utils import SERVICE_DISCOVERY_PHASES
from cmk.gui.openapi.api_endpoints.service_discovery.models.request_models import (
    UpdateDiscoveryPhaseModel,
)
from cmk.gui.watolib.services import ServiceDiscoveryBackgroundJob
from cmk.ruleset_matcher.labels import HostLabel
from cmk.utils.automation_config import LocalAutomationConfig
from cmk.utils.metrics import MetricTuple
from cmk.utils.servicename import ServiceName
from tests.testlib.gui.web_test_app import WebTestAppForCMK
from tests.testlib.rest_api_client import ClientRegistry

mock_discovery_result = ServiceDiscoveryPreviewResult(
    check_table=[
        CheckPreviewEntry(
            "unchanged",
            "cpu_loads",
            "cpu_load",
            None,
            None,
            {},
            {},
            {"levels": (5.0, 10.0)},
            "CPU load",
            0,
            "15 min load: 1.32 at 8 Cores (0.17 per Core)",
            [
                MetricTuple(name="load1", value=2.7, warn=40.0, crit=80.0, min_=0, max_=8),
                MetricTuple(name="load5", value=1.63, warn=40.0, crit=80.0, min_=0, max_=8),
                MetricTuple(name="load15", value=1.32, warn=40.0, crit=80.0, min_=0, max_=8),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "cpu_threads",
            "threads",
            None,
            None,
            {},
            {},
            {"levels": (2000, 4000)},
            "Number of threads",
            0,
            "Count: 1708 threads, Usage: 1.35%",
            [
                MetricTuple(
                    name="threads", value=1708, warn=2000.0, crit=4000.0, min_=None, max_=None
                ),
                MetricTuple(
                    name="thread_usage",
                    value=1.3496215054443164,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "new",
            "df",
            "filesystem",
            None,
            "/opt/omd/sites/heute/tmp",
            {"include_volume_name": False},
            {"include_volume_name": False},
            {
                "include_volume_name": False,
                "inodes_levels": (10.0, 5.0),
                "levels": (80.0, 90.0),
                "levels_low": (50.0, 60.0),
                "magic_normsize": 20,
                "show_inodes": "onlow",
                "show_levels": "onmagic",
                "show_reserved": False,
                "trend_perfdata": True,
                "trend_range": 24,
            },
            "Filesystem /opt/omd/sites/heute/tmp",
            0,
            "0.08% used (6.30 MB of 7.76 GB)",
            [
                MetricTuple(
                    name="fs_used",
                    value=6.30078125,
                    warn=6356.853125,
                    crit=7151.459765625,
                    min_=0,
                    max_=7946.06640625,
                ),
                MetricTuple(
                    name="fs_size", value=7946.06640625, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="fs_used_percent",
                    value=0.07929434424363863,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="inodes_used",
                    value=1558,
                    warn=1830773.7,
                    crit=1932483.3499999999,
                    min_=0.0,
                    max_=2034193.0,
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "new",
            "df",
            "filesystem",
            None,
            "/opt/omd/sites/old/tmp",
            {"include_volume_name": False},
            {"include_volume_name": False},
            {
                "include_volume_name": False,
                "inodes_levels": (10.0, 5.0),
                "levels": (80.0, 90.0),
                "levels_low": (50.0, 60.0),
                "magic_normsize": 20,
                "show_inodes": "onlow",
                "show_levels": "onmagic",
                "show_reserved": False,
                "trend_perfdata": True,
                "trend_range": 24,
            },
            "Filesystem /opt/omd/sites/old/tmp",
            0,
            "0% used (0.00 B of 7.76 GB)",
            [
                MetricTuple(
                    name="fs_used",
                    value=0.0,
                    warn=6356.853125,
                    crit=7151.459765625,
                    min_=0,
                    max_=7946.06640625,
                ),
                MetricTuple(
                    name="fs_size", value=7946.06640625, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="fs_used_percent", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="inodes_used",
                    value=1,
                    warn=1830773.7,
                    crit=1932483.3499999999,
                    min_=0.0,
                    max_=2034193.0,
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "new",
            "df",
            "filesystem",
            None,
            "/opt/omd/sites/stable/tmp",
            {"include_volume_name": False},
            {"include_volume_name": False},
            {
                "include_volume_name": False,
                "inodes_levels": (10.0, 5.0),
                "levels": (80.0, 90.0),
                "levels_low": (50.0, 60.0),
                "magic_normsize": 20,
                "show_inodes": "onlow",
                "show_levels": "onmagic",
                "show_reserved": False,
                "trend_perfdata": True,
                "trend_range": 24,
            },
            "Filesystem /opt/omd/sites/stable/tmp",
            0,
            "0.12% used (9.43 MB of 7.76 GB)",
            [
                MetricTuple(
                    name="fs_used",
                    value=9.42578125,
                    warn=6356.853125,
                    crit=7151.459765625,
                    min_=0,
                    max_=7946.06640625,
                ),
                MetricTuple(
                    name="fs_size", value=7946.06640625, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="fs_used_percent",
                    value=0.11862197933037819,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="inodes_used",
                    value=1412,
                    warn=1830773.7,
                    crit=1932483.3499999999,
                    min_=0.0,
                    max_=2034193.0,
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "new",
            "df",
            "filesystem",
            None,
            "/",
            {"include_volume_name": False},
            {"include_volume_name": False},
            {
                "include_volume_name": False,
                "inodes_levels": (10.0, 5.0),
                "levels": (80.0, 90.0),
                "levels_low": (50.0, 60.0),
                "magic_normsize": 20,
                "show_inodes": "onlow",
                "show_levels": "onmagic",
                "show_reserved": False,
                "trend_perfdata": True,
                "trend_range": 24,
            },
            "Filesystem /",
            0,
            "25.24% used (117.68 of 466.31 GB)",
            [
                MetricTuple(
                    name="fs_used",
                    value=120506.43359375,
                    warn=382000.025,
                    crit=429750.028125,
                    min_=0,
                    max_=477500.03125,
                ),
                MetricTuple(
                    name="fs_size", value=477500.03125, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="fs_used_percent",
                    value=25.236947792084568,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="inodes_used",
                    value=1131429,
                    warn=28009267.2,
                    crit=29565337.599999998,
                    min_=0.0,
                    max_=31121408.0,
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "df",
            "filesystem",
            None,
            "/boot/efi",
            {"include_volume_name": False},
            {"include_volume_name": False},
            {
                "include_volume_name": False,
                "inodes_levels": (10.0, 5.0),
                "levels": (80.0, 90.0),
                "levels_low": (50.0, 60.0),
                "magic_normsize": 20,
                "show_inodes": "onlow",
                "show_levels": "onmagic",
                "show_reserved": False,
                "trend_perfdata": True,
                "trend_range": 24,
            },
            "Filesystem /boot/efi",
            0,
            "3.0% used (15.33 of 510.98 MB)",
            [
                MetricTuple(
                    name="fs_used",
                    value=15.328125,
                    warn=408.7875,
                    crit=459.8859375,
                    min_=0,
                    max_=510.984375,
                ),
                MetricTuple(
                    name="fs_size", value=510.984375, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="fs_used_percent",
                    value=2.9997247958902853,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "new",
            "df",
            "filesystem",
            None,
            "/boot",
            {"include_volume_name": False},
            {"include_volume_name": False},
            {
                "include_volume_name": False,
                "inodes_levels": (10.0, 5.0),
                "levels": (80.0, 90.0),
                "levels_low": (50.0, 60.0),
                "magic_normsize": 20,
                "show_inodes": "onlow",
                "show_levels": "onmagic",
                "show_reserved": False,
                "trend_perfdata": True,
                "trend_range": 24,
            },
            "Filesystem /boot",
            0,
            "30.85% used (217.37 of 704.48 MB)",
            [
                MetricTuple(
                    name="fs_used",
                    value=217.3671875,
                    warn=563.5875,
                    crit=634.0359375,
                    min_=0,
                    max_=704.484375,
                ),
                MetricTuple(
                    name="fs_size", value=704.484375, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="fs_used_percent",
                    value=30.854791846873823,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="inodes_used",
                    value=305,
                    warn=42163.200000000004,
                    crit=44505.6,
                    min_=0.0,
                    max_=46848.0,
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "kernel_performance",
            "kernel_performance",
            None,
            None,
            {},
            {},
            {},
            "Kernel Performance",
            0,
            "WAITING - Counter based check, cannot be done offline",
            [
                MetricTuple(
                    name="process_creations", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="context_switches", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="major_page_faults", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="page_swap_in", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="page_swap_out", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "kernel_util",
            "cpu_iowait",
            None,
            None,
            {},
            {},
            {},
            "CPU utilization",
            0,
            "User: 14.7%, System: 12.14%, Wait: 0.1%, Total CPU: 26.95%",
            [
                MetricTuple(
                    name="user", value=14.70410082412248, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="system",
                    value=12.142805812602681,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="wait",
                    value=0.10180487170606699,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="util", value=26.948711508431227, warn=None, crit=None, min_=0, max_=None
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "lnx_thermal",
            "temperature",
            None,
            "Zone 0",
            {},
            {},
            {"device_levels_handling": "devdefault", "levels": (70.0, 80.0)},
            "Temperature Zone 0",
            0,
            "25.0 °C",
            [MetricTuple(name="temp", value=25.0, warn=107.0, crit=107.0, min_=None, max_=None)],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "lnx_thermal",
            "temperature",
            None,
            "Zone 1",
            {},
            {},
            {"device_levels_handling": "devdefault", "levels": (70.0, 80.0)},
            "Temperature Zone 1",
            0,
            "20.0 °C",
            [MetricTuple(name="temp", value=20.0, warn=70.0, crit=80.0, min_=None, max_=None)],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "lnx_thermal",
            "temperature",
            None,
            "Zone 2",
            {},
            {},
            {"device_levels_handling": "devdefault", "levels": (70.0, 80.0)},
            "Temperature Zone 2",
            0,
            "54.0 °C",
            [MetricTuple(name="temp", value=54.0, warn=78.0, crit=88.0, min_=None, max_=None)],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "lnx_thermal",
            "temperature",
            None,
            "Zone 3",
            {},
            {},
            {"device_levels_handling": "devdefault", "levels": (70.0, 80.0)},
            "Temperature Zone 3",
            0,
            "35.0 °C",
            [MetricTuple(name="temp", value=35.0, warn=70.0, crit=80.0, min_=None, max_=None)],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "lnx_thermal",
            "temperature",
            None,
            "Zone 4",
            {},
            {},
            {"device_levels_handling": "devdefault", "levels": (70.0, 80.0)},
            "Temperature Zone 4",
            0,
            "41.0 °C",
            [MetricTuple(name="temp", value=41.0, warn=70.0, crit=80.0, min_=None, max_=None)],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "lnx_thermal",
            "temperature",
            None,
            "Zone 5",
            {},
            {},
            {"device_levels_handling": "devdefault", "levels": (70.0, 80.0)},
            "Temperature Zone 5",
            0,
            "55.5 °C",
            [MetricTuple(name="temp", value=55.5, warn=115.0, crit=115.0, min_=None, max_=None)],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "lnx_thermal",
            "temperature",
            None,
            "Zone 6",
            {},
            {},
            {"device_levels_handling": "devdefault", "levels": (70.0, 80.0)},
            "Temperature Zone 6",
            0,
            "64.0 °C",
            [MetricTuple(name="temp", value=64.0, warn=99.0, crit=127.0, min_=None, max_=None)],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "lnx_thermal",
            "temperature",
            None,
            "Zone 7",
            {},
            {},
            {"device_levels_handling": "devdefault", "levels": (70.0, 80.0)},
            "Temperature Zone 7",
            1,
            "74.0 °C (warn/crit at 70.0/80.0 °C)",
            [MetricTuple(name="temp", value=74.0, warn=70.0, crit=80.0, min_=None, max_=None)],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "lnx_thermal",
            "temperature",
            None,
            "Zone 8",
            {},
            {},
            {"device_levels_handling": "devdefault", "levels": (70.0, 80.0)},
            "Temperature Zone 8",
            0,
            "38.0 °C",
            [MetricTuple(name="temp", value=38.0, warn=70.0, crit=80.0, min_=None, max_=None)],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "new",
            "mem_linux",
            "memory_linux",
            None,
            None,
            {},
            {},
            {
                "levels_commitlimit": ("perc_free", (20.0, 10.0)),
                "levels_committed": ("perc_used", (100.0, 150.0)),
                "levels_hardwarecorrupted": ("abs_used", (1, 1)),
                "levels_pagetables": ("perc_used", (8.0, 16.0)),
                "levels_shm": ("perc_used", (20.0, 30.0)),
                "levels_total": ("perc_used", (120.0, 150.0)),
                "levels_virtual": ("perc_used", (80.0, 90.0)),
                "levels_vmalloc": ("abs_free", (52428800, 31457280)),
            },
            "Memory",
            2,
            "Total virtual memory: 49.43% - 8.14 GB of 16.48 GB, RAM: 47.68% - 7.40 GB of 15.52 GB, Swap: 77.91% - 763.52 MB of 980.00 MB, Largest Free VMalloc Chunk: 0% free - 0.00 B of 32.00 TB VMalloc Area (warn/crit below 50.00 MB/30.00 MB free)(!!)",
            [
                MetricTuple(
                    name="active", value=8891592704, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="active_anon", value=7336378368, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="active_file", value=1555214336, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="anon_huge_pages", value=0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="anon_pages", value=7420919808, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(name="bounce", value=0, warn=None, crit=None, min_=None, max_=None),
                MetricTuple(
                    name="buffers", value=272564224, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="cached", value=3219124224, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="caches", value=4009385984, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(name="cma_free", value=0, warn=None, crit=None, min_=None, max_=None),
                MetricTuple(name="cma_total", value=0, warn=None, crit=None, min_=None, max_=None),
                MetricTuple(
                    name="commit_limit",
                    value=9359654912,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="committed_as",
                    value=16258154496,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="dirty", value=14913536, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="hardware_corrupted", value=0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="inactive", value=2157494272, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="inactive_anon",
                    value=1121906688,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="inactive_file",
                    value=1035587584,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="kreclaimable", value=361406464, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="kernel_stack", value=28037120, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="mapped", value=970366976, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="mem_available",
                    value=7177719808,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="mem_free", value=4710035456, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="mem_total", value=16664109056, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="mem_used", value=7944687616, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="mem_used_percent",
                    value=47.675441809110545,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="mlocked", value=81920, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="nfs_unstable", value=0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="page_tables", value=84729856, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="pending", value=14913536, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="percpu", value=9633792, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="sreclaimable", value=361406464, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="sunreclaim", value=257396736, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="shmem", value=934322176, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="shmem_huge_pages", value=0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="shmem_pmd_mapped", value=0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="slab", value=618803200, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="swap_cached", value=156291072, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="swap_free", value=226992128, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="swap_total", value=1027600384, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="swap_used", value=800608256, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="total_total",
                    value=17691709440,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="total_used", value=8745295872, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="unevictable", value=19808256, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(name="writeback", value=0, warn=None, crit=None, min_=None, max_=None),
                MetricTuple(
                    name="writeback_tmp", value=0, warn=None, crit=None, min_=None, max_=None
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "mkeventd_status",
            None,
            None,
            HostName("heute"),
            {},
            {},
            {},
            "OMD heute Event Console",
            0,
            "WAITING - Counter based check, cannot be done offline",
            [
                MetricTuple(
                    name="num_open_events", value=0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="process_virtual_size",
                    value=218300416,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="average_message_rate",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="average_rule_hit_rate",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="average_rule_trie_rate",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="average_drop_rate", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="average_event_rate", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="average_connect_rate",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="average_request_time",
                    value=0.00027762370400620984,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "mkeventd_status",
            None,
            None,
            "stable",
            {},
            {},
            {},
            "OMD stable Event Console",
            0,
            "WAITING - Counter based check, cannot be done offline",
            [
                MetricTuple(
                    name="num_open_events", value=0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="process_virtual_size",
                    value=205152256,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="average_message_rate",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="average_rule_hit_rate",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="average_rule_trie_rate",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="average_drop_rate", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="average_event_rate", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="average_connect_rate",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="average_request_time",
                    value=0.00039733688471126213,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "mknotifyd",
            None,
            None,
            HostName("heute"),
            {},
            {},
            {},
            "OMD heute Notification Spooler",
            0,
            "Version: 2020.06.08, Spooler running",
            [
                MetricTuple(
                    name="last_updated", value=20, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(name="new_files", value=0, warn=None, crit=None, min_=None, max_=None),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "mknotifyd",
            None,
            None,
            "stable",
            {},
            {},
            {},
            "OMD stable Notification Spooler",
            0,
            "Version: 1.6.0-2020.06.05, Spooler running",
            [
                MetricTuple(
                    name="last_updated", value=12, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(name="new_files", value=0, warn=None, crit=None, min_=None, max_=None),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "mounts",
            "fs_mount_options",
            None,
            "/",
            {"mount_options": ["errors=remount-ro", "relatime", "rw"]},
            {"mount_options": ["errors=remount-ro", "relatime", "rw"]},
            {"mount_options": ["errors=remount-ro", "relatime", "rw"]},
            "Mount options of /",
            0,
            "Mount options exactly as expected",
            [],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "mounts",
            "fs_mount_options",
            None,
            "/boot",
            {"mount_options": ["relatime", "rw"]},
            {"mount_options": ["relatime", "rw"]},
            {"mount_options": ["relatime", "rw"]},
            "Mount options of /boot",
            0,
            "Mount options exactly as expected",
            [],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "mounts",
            "fs_mount_options",
            None,
            "/boot/efi",
            {
                "mount_options": [
                    "codepage=437",
                    "dmask=0077",
                    "errors=remount-ro",
                    "fmask=0077",
                    "iocharset=iso8859-1",
                    "relatime",
                    "rw",
                    "shortname=mixed",
                ]
            },
            {
                "mount_options": [
                    "codepage=437",
                    "dmask=0077",
                    "errors=remount-ro",
                    "fmask=0077",
                    "iocharset=iso8859-1",
                    "relatime",
                    "rw",
                    "shortname=mixed",
                ]
            },
            {
                "mount_options": [
                    "codepage=437",
                    "dmask=0077",
                    "errors=remount-ro",
                    "fmask=0077",
                    "iocharset=iso8859-1",
                    "relatime",
                    "rw",
                    "shortname=mixed",
                ]
            },
            "Mount options of /boot/efi",
            0,
            "Mount options exactly as expected",
            [],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "omd_apache",
            None,
            None,
            "heute",
            {},
            {},
            {},
            "OMD heute apache",
            0,
            "WAITING - Counter based check, cannot be done offline",
            [
                MetricTuple(
                    name="requests_images", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_snapins",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="requests_styles", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_scripts", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_wato", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_views", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_bi", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_api", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_ajax", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_index", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_login", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_search",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="requests_cmk_sidebar",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="requests_cmk_graphs",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="requests_cmk_dashboards",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="requests_nagvis_snapin",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="requests_nagvis_ajax",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="requests_nagvis_other",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="requests_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_snapins", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_scripts", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_wato", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_images", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_styles", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_views", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_bi", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_api", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_ajax", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_index", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_login", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_search", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_sidebar", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_graphs", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_dashboards",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="secs_nagvis_snapin", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_nagvis_ajax", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_nagvis_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_scripts", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_styles", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_snapins", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_wato", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_images", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_views", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_bi", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_api", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_ajax", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_index", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_login", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_search", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_sidebar", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_graphs", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_dashboards",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="bytes_nagvis_snapin",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="bytes_nagvis_ajax", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_nagvis_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "omd_apache",
            None,
            None,
            "stable",
            {},
            {},
            {},
            "OMD stable apache",
            0,
            "WAITING - Counter based check, cannot be done offline",
            [
                MetricTuple(
                    name="requests_cmk_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_views", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_wato", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_bi", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_cmk_snapins",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="requests_cmk_dashboards",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="requests_nagvis_snapin",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="requests_nagvis_ajax",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="requests_nagvis_other",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="requests_images", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_styles", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_scripts", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="requests_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_views", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_wato", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_bi", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_snapins", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_cmk_dashboards",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="secs_nagvis_snapin", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_nagvis_ajax", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_nagvis_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_images", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_styles", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_scripts", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="secs_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_views", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_wato", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_bi", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_snapins", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_cmk_dashboards",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="bytes_nagvis_snapin",
                    value=0.0,
                    warn=None,
                    crit=None,
                    min_=None,
                    max_=None,
                ),
                MetricTuple(
                    name="bytes_nagvis_ajax", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_nagvis_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_images", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_styles", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_scripts", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(
                    name="bytes_other", value=0.0, warn=None, crit=None, min_=None, max_=None
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "systemd_units_services_summary",
            "systemd_services_summary",
            None,
            "Summary",
            {},
            {"states": {"active": 0, "failed": 2, "inactive": 0}, "states_default": 2},
            {"states": {"active": 0, "failed": 2, "inactive": 0}, "states_default": 2},
            "Systemd Service Summary",
            0,
            "138 services in total, Service 'kubelet' activating for: 0.00 s, 5 disabled services",
            [],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "tcp_conn_stats",
            "tcp_conn_stats",
            None,
            None,
            {},
            {},
            {},
            "TCP Connections",
            0,
            "CLOSE_WAIT: 5, ESTABLISHED: 13, FIN_WAIT2: 1, LISTEN: 21, SYN_SENT: 1, TIME_WAIT: 108",
            [
                MetricTuple(name="CLOSED", value=0, warn=None, crit=None, min_=None, max_=None),
                MetricTuple(name="CLOSE_WAIT", value=5, warn=None, crit=None, min_=None, max_=None),
                MetricTuple(name="CLOSING", value=0, warn=None, crit=None, min_=None, max_=None),
                MetricTuple(
                    name="ESTABLISHED", value=13, warn=None, crit=None, min_=None, max_=None
                ),
                MetricTuple(name="FIN_WAIT1", value=0, warn=None, crit=None, min_=None, max_=None),
                MetricTuple(name="FIN_WAIT2", value=1, warn=None, crit=None, min_=None, max_=None),
                MetricTuple(name="LAST_ACK", value=0, warn=None, crit=None, min_=None, max_=None),
                MetricTuple(name="LISTEN", value=21, warn=None, crit=None, min_=None, max_=None),
                MetricTuple(name="SYN_RECV", value=0, warn=None, crit=None, min_=None, max_=None),
                MetricTuple(name="SYN_SENT", value=1, warn=None, crit=None, min_=None, max_=None),
                MetricTuple(
                    name="TIME_WAIT", value=108, warn=None, crit=None, min_=None, max_=None
                ),
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "unchanged",
            "uptime",
            "uptime",
            None,
            None,
            {},
            {},
            {},
            "Uptime",
            0,
            "Up since Tue Jun  2 07:50:48 2020, uptime: 7 days, 7:30:46",
            [
                MetricTuple(
                    name="uptime", value=631846.94, warn=None, crit=None, min_=None, max_=None
                )
            ],
            {},
            {},
            [HostName("heute")],
        ),
        CheckPreviewEntry(
            "active",
            "cmk_inv",
            None,
            None,
            "Check_MK HW/SW Inventory",
            {},
            {},
            {},
            "Check_MK HW/SW Inventory",
            None,
            "WAITING - Active check, cannot be done offline",
            [],
            {},
            {},
            [HostName("heute")],
        ),
    ],
    nodes_check_table={},
    host_labels={"cmk/check_mk_server": {"plugin_name": "labels", "value": "yes"}},
    output="+ FETCHING DATA\n [agent] Using data from cache file /omd/sites/heute/tmp/check_mk/cache/heute\n [agent] Use cached data\n [piggyback] Execute data source\nNo piggyback files for 'heute'. Skip processing.\nNo piggyback files for '127.0.0.1'. Skip processing.\n+ EXECUTING DISCOVERY PLUGINS (29)\nkernel does not support discovery. Skipping it.\n+ EXECUTING HOST LABEL DISCOVERY\n",
    new_labels={},
    vanished_labels={},
    changed_labels={},
    source_results=[(0, "Success")],
    labels_by_host={
        HostName("heute"): [HostLabel("cmk/check_mk_server", "yes", SectionName("labels"))]
    },
    config_warnings=["Don't do this again!"],
)


@pytest.fixture(name="mock_discovery_preview")
def fixture_mock_discovery_preview(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "cmk.gui.watolib.services.local_discovery_preview", return_value=mock_discovery_result
    )


@pytest.fixture(name="mock_discovery")
def fixture_mock_discovery(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("cmk.gui.watolib.services.local_discovery", return_value=None)


@pytest.fixture(name="mock_set_autochecks")
def fixture_mock_set_autochecks(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "cmk.gui.watolib.services.set_autochecks_v2", return_value=SetAutochecksV2Result()
    )


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
def test_openapi_discovery_fails_on_invalid_content_type(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_discovery_preview: MagicMock,
    mock_set_autochecks: MagicMock,
) -> None:
    resp = aut_user_auth_wsgi_app.post(
        f"{base}/domain-types/service_discovery_run/actions/start/invoke",
        params='{"mode": "foo", "host_name": "example.com"}',
        headers={"Accept": "application/json"},
        status=415,
    )
    assert "Content type not valid" in resp.json["title"]
    mock_discovery_preview.assert_not_called()
    mock_set_autochecks.assert_not_called()


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
def test_openapi_discovery_on_invalid_mode(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_discovery_preview: MagicMock,
    mock_set_autochecks: MagicMock,
) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        f"{base}/domain-types/service_discovery_run/actions/start/invoke",
        params='{"mode": "foo", "host_name": "example.com"}',
        content_type="application/json",
        headers={"Accept": "application/json"},
        status=400,
    )
    assert resp.json["detail"] == "These fields have problems: body.mode"
    mock_discovery_preview.assert_not_called()
    mock_set_autochecks.assert_not_called()


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
def test_openapi_discovery_refresh_services(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_discovery_preview: MagicMock,
    mock_set_autochecks: MagicMock,
) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        f"{base}/domain-types/service_discovery_run/actions/start/invoke",
        params='{"mode": "refresh", "host_name": "example.com"}',
        content_type="application/json",
        headers={"Accept": "application/json"},
        status=303,
    )
    assert (
        resp.location
        == "/NO_SITE/check_mk/api/v1/objects/service_discovery_run/example.com/actions/wait-for-completion/invoke"
    )
    assert mock_discovery_preview.mock_calls == [
        call("example.com", prevent_fetching=False, raise_errors=False, debug=False),
        call("example.com", prevent_fetching=False, raise_errors=False, debug=False),
    ]
    mock_set_autochecks.assert_not_called()


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
def test_openapi_discovery_tabula_rasa(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_set_autochecks: MagicMock,
    mock_discovery_preview: MagicMock,
    mock_discovery: MagicMock,
) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        f"{base}/domain-types/service_discovery_run/actions/start/invoke",
        params='{"mode": "tabula_rasa", "host_name": "example.com"}',
        content_type="application/json",
        headers={"Accept": "application/json"},
        status=303,
    )
    mock_set_autochecks.assert_not_called()
    assert mock_discovery.mock_calls == [
        call(
            DiscoverySettings(
                update_host_labels=True,
                add_new_services=True,
                remove_vanished_services=True,
                update_changed_service_labels=True,
                update_changed_service_parameters=True,
            ),
            ["example.com"],
            scan=True,
            raise_errors=False,
            non_blocking_http=True,
            debug=False,
        )
    ]
    assert mock_discovery_preview.mock_calls == [
        call("example.com", prevent_fetching=False, raise_errors=False, debug=False),
        call("example.com", prevent_fetching=True, raise_errors=False, debug=False),
    ]


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
def test_openapi_discovery_disable_and_re_enable_one_service(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_discovery_preview: MagicMock,
    mock_set_autochecks: MagicMock,
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        # one would like to mock the call in the library and not the import. WHY????
        "cmk.gui.watolib.rulesets.get_services_labels",
        return_value=GetServicesLabelsResult(labels=defaultdict(dict)),
    )
    mocker.patch(
        "cmk.gui.watolib.rulesets.analyze_service_rule_matches",
        return_value=AnalyzeServiceRuleMatchesResult({}),
    )
    aut_user_auth_wsgi_app.call_method(
        "post",
        f"{base}/domain-types/service_discovery_run/actions/start/invoke",
        params='{"mode": "refresh", "host_name": "example.com"}',
        content_type="application/json",
        headers={"Accept": "application/json"},
        status=303,
    )
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        f"{base}/objects/service_discovery/example.com",
        headers={"Accept": "application/json"},
        status=200,
    )
    mock_discovery_preview.reset_mock()
    df_boot_ignore = aut_user_auth_wsgi_app.follow_link(
        resp,
        "cmk/service.move-ignored",
        json_data=resp.json["extensions"]["check_table"]["df-/boot"],
        headers={"Accept": "application/json"},
        status=204,
    )
    assert df_boot_ignore.text == ""
    mock_discovery_preview.assert_called_once()
    mock_discovery_preview.reset_mock()
    sample_host_name = HostName("example.com")
    expected_autochecks: Mapping[ServiceName, AutocheckEntry] = {
        "CPU load": AutocheckEntry(CheckPluginName("cpu_loads"), None, {}, {}),
        "Number of threads": AutocheckEntry(CheckPluginName("cpu_threads"), None, {}, {}),
        "Filesystem /boot/efi": AutocheckEntry(
            CheckPluginName("df"), "/boot/efi", {"include_volume_name": False}, {}
        ),
        "Kernel Performance": AutocheckEntry(CheckPluginName("kernel_performance"), None, {}, {}),
        "CPU utilization": AutocheckEntry(CheckPluginName("kernel_util"), None, {}, {}),
        "Temperature Zone 0": AutocheckEntry(CheckPluginName("lnx_thermal"), "Zone 0", {}, {}),
        "Temperature Zone 1": AutocheckEntry(CheckPluginName("lnx_thermal"), "Zone 1", {}, {}),
        "Temperature Zone 2": AutocheckEntry(CheckPluginName("lnx_thermal"), "Zone 2", {}, {}),
        "Temperature Zone 3": AutocheckEntry(CheckPluginName("lnx_thermal"), "Zone 3", {}, {}),
        "Temperature Zone 4": AutocheckEntry(CheckPluginName("lnx_thermal"), "Zone 4", {}, {}),
        "Temperature Zone 5": AutocheckEntry(CheckPluginName("lnx_thermal"), "Zone 5", {}, {}),
        "Temperature Zone 6": AutocheckEntry(CheckPluginName("lnx_thermal"), "Zone 6", {}, {}),
        "Temperature Zone 7": AutocheckEntry(CheckPluginName("lnx_thermal"), "Zone 7", {}, {}),
        "Temperature Zone 8": AutocheckEntry(CheckPluginName("lnx_thermal"), "Zone 8", {}, {}),
        "OMD heute Event Console": AutocheckEntry(
            CheckPluginName("mkeventd_status"), "heute", {}, {}
        ),
        "OMD stable Event Console": AutocheckEntry(
            CheckPluginName("mkeventd_status"), "stable", {}, {}
        ),
        "OMD heute Notification Spooler": AutocheckEntry(
            CheckPluginName("mknotifyd"), "heute", {}, {}
        ),
        "OMD stable Notification Spooler": AutocheckEntry(
            CheckPluginName("mknotifyd"), "stable", {}, {}
        ),
        "Mount options of /": AutocheckEntry(
            CheckPluginName("mounts"),
            "/",
            {"mount_options": ["errors=remount-ro", "relatime", "rw"]},
            {},
        ),
        "Mount options of /boot": AutocheckEntry(
            CheckPluginName("mounts"), "/boot", {"mount_options": ["relatime", "rw"]}, {}
        ),
        "Mount options of /boot/efi": AutocheckEntry(
            CheckPluginName("mounts"),
            "/boot/efi",
            {
                "mount_options": [
                    "codepage=437",
                    "dmask=0077",
                    "errors=remount-ro",
                    "fmask=0077",
                    "iocharset=iso8859-1",
                    "relatime",
                    "rw",
                    "shortname=mixed",
                ]
            },
            {},
        ),
        "OMD heute apache": AutocheckEntry(CheckPluginName("omd_apache"), "heute", {}, {}),
        "OMD stable apache": AutocheckEntry(CheckPluginName("omd_apache"), "stable", {}, {}),
        "Systemd Service Summary": AutocheckEntry(
            CheckPluginName("systemd_units_services_summary"), "Summary", {}, {}
        ),
        "TCP Connections": AutocheckEntry(CheckPluginName("tcp_conn_stats"), None, {}, {}),
        "Uptime": AutocheckEntry(CheckPluginName("uptime"), None, {}, {}),
    }
    mock_set_autochecks.assert_called_once_with(
        LocalAutomationConfig(),
        SetAutochecksInput(
            sample_host_name,
            expected_autochecks,
            {},
        ),
        debug=False,
    )
    mock_set_autochecks.reset_mock()

    df_boot_monitor = aut_user_auth_wsgi_app.follow_link(
        resp,
        "cmk/service.move-monitored",
        json_data=resp.json["extensions"]["check_table"]["df-/boot"],
        headers={"Accept": "application/json"},
        status=204,
    )
    assert df_boot_monitor.text == ""
    mock_discovery_preview.assert_called_once()
    expected_autochecks_2: Mapping[ServiceName, AutocheckEntry] = {
        **expected_autochecks,
        "Filesystem /boot": AutocheckEntry(
            CheckPluginName("df"), "/boot", {"include_volume_name": False}, {}
        ),
    }
    mock_set_autochecks.assert_called_once_with(
        LocalAutomationConfig(),
        SetAutochecksInput(
            sample_host_name,
            expected_autochecks_2,
            {},
        ),
        debug=False,
    )


@pytest.mark.usefixtures("inline_background_jobs")
def test_openapi_bulk_discovery_with_default_options(
    base: str, clients: ClientRegistry, mocker: MockerFixture
) -> None:
    # create some sample hosts
    clients.HostConfig.bulk_create(
        entries=[
            {
                "host_name": "foobar",
                "folder": "/",
            },
            {
                "host_name": "sample",
                "folder": "/",
            },
        ]
    )

    automation = mocker.patch("cmk.gui.watolib.bulk_discovery.discovery")
    resp = clients.ServiceDiscovery.bulk_discovery(
        hostnames=["foobar", "sample"],
        monitor_undecided_services=True,
        follow_redirects=False,
    )
    automation.assert_called_once()
    assert resp.status_code == 303


def test_openapi_bulk_discovery_with_invalid_hostname(
    base: str,
    clients: ClientRegistry,
) -> None:
    resp = clients.ServiceDiscovery.bulk_discovery(hostnames=["wrong_hostname"], expect_ok=False)
    resp.assert_status_code(400)


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
def test_openapi_refresh_job_status(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_discovery_preview: MagicMock,
) -> None:
    host_name = "example.com"

    aut_user_auth_wsgi_app.call_method(
        "get",
        f"{base}/objects/service_discovery_run/example.com/actions/wait-for-completion/invoke",
        headers={"Accept": "application/json"},
        status=404,
    )

    aut_user_auth_wsgi_app.call_method(
        "post",
        f"{base}/domain-types/service_discovery_run/actions/start/invoke",
        params='{"mode": "refresh", "host_name": "example.com"}',
        content_type="application/json",
        headers={"Accept": "application/json"},
        status=303,
    )

    aut_user_auth_wsgi_app.call_method(
        "get",
        f"{base}/objects/service_discovery_run/example.com/actions/wait-for-completion/invoke",
        headers={"Accept": "application/json"},
        status=204,
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/objects/service_discovery_run/{host_name}",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert resp.json["id"] == resp.json["id"]
    assert "active" in resp.json["extensions"]
    assert "state" in resp.json["extensions"]
    assert "result" in resp.json["extensions"]["logs"]
    assert "progress" in resp.json["extensions"]["logs"]


@pytest.mark.usefixtures("inline_background_jobs")
def test_openapi_service_discovery_accessible_to_folder_contact(
    clients: ClientRegistry,
    mock_discovery_preview: MagicMock,
) -> None:
    """Regression test for SUP-29084.

    A user who can see a host only through their contact group's folder permissions (not
    through the blanket 'wato.see_all_folders' permission, which is only held by admins) must
    still be able to run a service discovery and read back its result/status via the REST API.
    """
    host_name = "restricted_host"
    clients.ContactGroup.create("folder_cg", alias="folder_cg")
    clients.User.create(
        username="folder_member",
        fullname="folder_member",
        customer=None,
        roles=["user"],
        contactgroups=["folder_cg"],
        auth_option={"auth_type": "password", "password": "supersecretish"},
    )
    clients.Folder.create(
        title="restricted_folder",
        parent="/",
        folder_name="restricted_folder",
        attributes={"contactgroups": {"groups": ["folder_cg"], "recurse_perms": True}},
    )
    clients.HostConfig.create(host_name=host_name, folder="/restricted_folder")

    clients.ServiceDiscovery.set_credentials("folder_member", "supersecretish")

    clients.ServiceDiscovery.start_service_discovery(host_name, "refresh").assert_status_code(303)

    clients.ServiceDiscovery.wait_for_service_discovery_completion(host_name).assert_status_code(
        204
    )

    run_resp = clients.ServiceDiscovery.get_service_discovery_status(host_name)

    run_resp.assert_status_code(200)
    assert run_resp.json["extensions"]["state"] == "finished"


def test_openapi_service_discovery_inaccessible_to_non_folder_contact(
    clients: ClientRegistry,
) -> None:
    """A user who is NOT a member of the host folder's contact group gets 404, indistinguishable
    from a host that does not exist, so that host existence is not leaked."""
    host_name = "restricted_host"
    clients.ContactGroup.create("correct_cg", alias="correct_cg")
    clients.ContactGroup.create("wrong_cg", alias="wrong_cg")
    clients.User.create(
        username="wrong_member",
        fullname="wrong_member",
        customer=None,
        roles=["user"],
        contactgroups=["wrong_cg"],
        auth_option={"auth_type": "password", "password": "supersecretish"},
    )
    clients.Folder.create(
        title="restricted_folder",
        parent="/",
        folder_name="restricted_folder",
        attributes={"contactgroups": {"groups": ["correct_cg"], "recurse_perms": True}},
    )
    clients.HostConfig.create(host_name=host_name, folder="/restricted_folder")

    clients.ServiceDiscovery.set_credentials("wrong_member", "supersecretish")

    clients.ServiceDiscovery.wait_for_service_discovery_completion(
        host_name, expect_ok=False
    ).assert_status_code(404)


@pytest.mark.usefixtures("inline_background_jobs")
def test_openapi_service_discovery_accessible_to_admin_not_in_folder_contact_group(
    clients: ClientRegistry,
    mock_discovery_preview: MagicMock,
) -> None:
    """Regression test for SUP-29084.

    Admins can see every host via the blanket 'wato.see_all_folders' permission, regardless of
    contact group membership. This must keep working now that 'wato.see_all_folders' is only an
    optional shortcut in RO_PERMISSIONS (added so that folder contacts without it are not locked
    out, see test_openapi_service_discovery_accessible_to_folder_contact).
    """
    host_name = "restricted_host"
    clients.ContactGroup.create("folder_cg", alias="folder_cg")
    clients.Folder.create(
        title="restricted_folder",
        parent="/",
        folder_name="restricted_folder",
        attributes={"contactgroups": {"groups": ["folder_cg"], "recurse_perms": True}},
    )
    clients.HostConfig.create(host_name=host_name, folder="/restricted_folder")

    clients.ServiceDiscovery.start_service_discovery(host_name, "refresh").assert_status_code(303)

    clients.ServiceDiscovery.wait_for_service_discovery_completion(host_name).assert_status_code(
        204
    )

    run_resp = clients.ServiceDiscovery.get_service_discovery_status(host_name)

    run_resp.assert_status_code(200)
    assert run_resp.json["extensions"]["state"] == "finished"


# --------------------------------------------------------------------------------------------
# Tier 3 -- REST characterization
#
# Specified in `packages/cmk-check-engine/docs/SERVICE_DISCOVERY_BEHAVIOUR_MATRIX.md` §7.
#
# Tier 1 pins the transition function, purely and exhaustively. Tier 2 pins the dispatch and the
# side effects one layer out. This tier pins only what neither of them can see: the HTTP boundary
# -- which request bodies are accepted, which status codes come back, which permission a real role
# is actually stopped by, and where a redirect points. It deliberately does *not* re-assert the
# matrix cells; the tests below assert on the set of services that reached `set_autochecks_v2`,
# which is the coarsest observation that still distinguishes the modes and phases from one another.
#
# **No `xfail(strict=True)` tripwires live in this tier, on purpose.** Tiers 1 and 2 already carry
# one for eleven of the thirteen §10 tickets, each at the lowest layer that can see its divergence,
# and a second tripwire for the same ticket up here would give whoever fixes it two pairs to find
# instead of one. This tier sits above the endpoint registry, the request model, the permission
# decorators and a Flask app, so a strict xfail here could also flip for a reason that has nothing
# to do with its ticket -- announcing a fix that did not happen. The divergences below are
# therefore pinned as plain characterization tests that name their ticket in a comment; each one
# asserts a status code or a service set that the fix must change, so the fix reddens this file and
# the comment says what to do about it.
# --------------------------------------------------------------------------------------------

TIER3_HOST = HostName("example.com")
TIER3_PLUGIN = "df"

#: One row per interesting `check_source`, so that every mode and every target phase has something
#: to act on and something to leave alone. Item and description are derived from the source, which
#: makes the assertions below readable as "which rows survived".
TIER3_SOURCES = ("unchanged", "changed", "new", "vanished", "ignored")

#: The services in the autochecks file when nothing has been asked of the host: the two monitored
#: ones plus the vanished one, which stays until it is explicitly removed. `new` and `ignored` are
#: absent -- an undecided service was never adopted, and a row already classified `ignored` is
#: deliberately kept out of the write unless it is being re-monitored (`_case_ignored` writes only
#: on target `MONITORED`; the comment there cites CMK-33299 for the rule). §10.1 is that the
#: handlers for the *other* sources do not honour the same rule.
TIER3_BASELINE = frozenset({"Filesystem /unchanged", "Filesystem /changed", "Filesystem /vanished"})

TIER3_OLD_PARAMS: Mapping[str, str] = {"p": "old"}
TIER3_NEW_PARAMS: Mapping[str, str] = {"p": "new"}
TIER3_OLD_LABELS: Mapping[str, str] = {"l": "old"}
TIER3_NEW_LABELS: Mapping[str, str] = {"l": "new"}


def tier3_service(source: str) -> str:
    return f"Filesystem /{source}"


def tier3_entry(check_source: str) -> CheckPreviewEntry:
    """A preview row whose old and new values differ, so value adoption is observable."""
    return CheckPreviewEntry(
        check_source=check_source,
        check_plugin_name=TIER3_PLUGIN,
        ruleset_name="filesystem",
        discovery_ruleset_name=None,
        item=f"/{check_source}",
        old_discovered_parameters=TIER3_OLD_PARAMS,
        new_discovered_parameters=TIER3_NEW_PARAMS,
        effective_parameters={},
        description=tier3_service(check_source),
        state=0,
        output="",
        metrics=[],
        old_labels=TIER3_OLD_LABELS,
        new_labels=TIER3_NEW_LABELS,
        found_on_nodes=[TIER3_HOST],
    )


class Tier3Writes:
    """What one request sent to the automations that persist a discovery.

    All three are recorded -- `set_autochecks_v2`, `update_host_labels` and `local_discovery` --
    because "nothing was written" is only a meaningful assertion if the other doors are watched
    as well. A mode that writes no autochecks may still be doing its whole job through the
    host-label automation or through a rediscovery, and a mode that does nothing at all has to be
    distinguishable from both.
    """

    def __init__(
        self,
        set_autochecks: MagicMock,
        update_host_labels: MagicMock,
        local_discovery: MagicMock,
    ) -> None:
        self._set_autochecks = set_autochecks
        self._update_host_labels = update_host_labels
        self._local_discovery = local_discovery

    @property
    def inputs(self) -> list[SetAutochecksInput]:
        """The `SetAutochecksInput` of each write, in order."""
        return [invocation.args[1] for invocation in self._set_autochecks.call_args_list]

    @property
    def services(self) -> list[frozenset[str]]:
        """One entry per write: the service names the autochecks file would hold afterwards."""
        return [frozenset(written.target_services) for written in self.inputs]

    def written(self, service: str) -> AutocheckEntry:
        """The entry written for `service` by the single write this request made."""
        (only,) = self.inputs
        return only.target_services[service]

    @property
    def host_labels(self) -> list[HostName]:
        """The host each `update_host_labels` call was for, in order."""
        return [invocation.args[1] for invocation in self._update_host_labels.call_args_list]

    @property
    def scans(self) -> list[DiscoverySettings]:
        """The `DiscoverySettings` of each `local_discovery` call -- the rediscovery door.

        `tabula_rasa` writes through here rather than through `set_autochecks_v2`, so asserting
        only on autochecks cannot tell it apart from a mode that does nothing.
        """
        return [invocation.args[0] for invocation in self._local_discovery.call_args_list]


@pytest.fixture(name="tier3_writes")
def fixture_tier3_writes(mocker: MockerFixture) -> Tier3Writes:
    """Patch everything that leaves the process, and record the autochecks writes.

    The preview is patched rather than the automation transport (as Tier 2 does): this tier is
    about the HTTP boundary, and every endpoint here runs on the local site, so the read path's
    local/remote branch -- which is what Tier 2 exists to pin -- is not in question. The
    consequence is that a re-read after a write returns the *same* canned table, so the
    `check_table` in a response body cannot show the effect of the action. That is why the
    assertions below are on the writes and not on the response.
    """
    mocker.patch(
        "cmk.gui.watolib.services.local_discovery_preview",
        return_value=ServiceDiscoveryPreviewResult(
            output="",
            check_table=[tier3_entry(source) for source in TIER3_SOURCES],
            nodes_check_table={},
            host_labels={"cmk/tier3": {"plugin_name": "labels", "value": "yes"}},
            new_labels={},
            vanished_labels={},
            changed_labels={},
            labels_by_host={TIER3_HOST: [HostLabel("cmk/tier3", "yes", SectionName("labels"))]},
            source_results=[(0, "Success")],
            config_warnings=[],
        ),
    )
    local_discovery = mocker.patch("cmk.gui.watolib.services.local_discovery", return_value=None)
    update_host_labels = mocker.patch(
        "cmk.gui.watolib.services.update_host_labels", return_value=UpdateHostLabelsResult()
    )
    # The disabled-services rule editor runs whenever a row is or becomes `ignored`.
    mocker.patch(
        "cmk.gui.watolib.rulesets.get_services_labels",
        return_value=GetServicesLabelsResult(labels=defaultdict(dict)),
    )
    mocker.patch(
        "cmk.gui.watolib.rulesets.analyze_service_rule_matches",
        return_value=AnalyzeServiceRuleMatchesResult({}),
    )
    return Tier3Writes(
        mocker.patch(
            "cmk.gui.watolib.services.set_autochecks_v2", return_value=SetAutochecksV2Result()
        ),
        update_host_labels,
        local_discovery,
    )


# --- T3.1 / §5, §10.5: what each of the five immediate API modes writes ---------------------
#
# `refresh` and `tabula_rasa` are the other two of the seven; they redirect instead of answering
# with a result and are T3.5, two sections down.

#: Per mode: the services the autochecks file holds afterwards, and whether the host-label
#: automation ran. Every mode makes exactly one autochecks write except `only_host_labels`, which
#: makes none -- so that mode is asserted by what it *does* do, not only by an absence.
#:
#: `only_service_labels` is the divergence: it writes the same four services as `new` although the
#: only row it is documented to touch is the `changed` one (§10.5, CMK-38599). The mechanism
#: differs -- `new` retargets one row and writes four because the file is rebuilt from scratch
#: (§1), while `only_service_labels` retargets all four -- but the payload cannot tell them apart.
#: The value-adoption tests below can.
_MODE_WRITES: Mapping[str, tuple[frozenset[str] | None, bool]] = {
    "new": (TIER3_BASELINE | {tier3_service("new")}, False),
    "remove": (TIER3_BASELINE - {tier3_service("vanished")}, False),
    "fix_all": ((TIER3_BASELINE | {tier3_service("new")}) - {tier3_service("vanished")}, True),
    "only_host_labels": (None, True),
    "only_service_labels": (TIER3_BASELINE | {tier3_service("new")}, False),
}


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
@pytest.mark.parametrize(
    "mode, expected_services, expects_host_labels",
    [(mode, services, labels) for mode, (services, labels) in _MODE_WRITES.items()],
    ids=list(_MODE_WRITES),
)
def test_api_mode_matrix(
    clients: ClientRegistry,
    tier3_writes: Tier3Writes,
    mode: str,
    expected_services: frozenset[str] | None,
    expects_host_labels: bool,
) -> None:
    """§5: each mode answers `200` and rewrites the autochecks file from scratch (§1).

    The host-label column is what keeps `only_host_labels` honest. Asserting only that it writes
    no autochecks would pass for a mode that had become a complete no-op; asserting that it also
    updates the host's labels is the half that says it did its job.
    """
    clients.ServiceDiscovery.start_service_discovery(str(TIER3_HOST), mode).assert_status_code(200)

    assert tier3_writes.services == ([] if expected_services is None else [expected_services])
    assert tier3_writes.host_labels == ([TIER3_HOST] if expects_host_labels else [])


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
def test_monitoring_an_undecided_service_does_not_adopt_its_new_values(
    clients: ClientRegistry, tier3_writes: Tier3Writes
) -> None:
    """A3-F1: `new` writes the service it just accepted with the values it had *before*.

    The row's newly discovered parameters and labels are in the same preview entry the mode read,
    and are discarded. `fix_all` on the same table adopts them, which is what makes this a
    divergence between modes rather than a property of the accept itself.
    """
    clients.ServiceDiscovery.start_service_discovery(str(TIER3_HOST), "new")

    accepted = tier3_writes.written(tier3_service("new"))
    assert accepted.parameters == TIER3_OLD_PARAMS
    assert accepted.service_labels == TIER3_OLD_LABELS


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
def test_fix_all_adopts_both_parameters_and_labels_of_a_changed_service(
    clients: ClientRegistry, tier3_writes: Tier3Writes
) -> None:
    """§5 Matrix A3: "Accept all" is the mode that takes the new values."""
    clients.ServiceDiscovery.start_service_discovery(str(TIER3_HOST), "fix_all")

    changed = tier3_writes.written(tier3_service("changed"))
    assert changed.parameters == TIER3_NEW_PARAMS
    assert changed.service_labels == TIER3_NEW_LABELS


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
def test_update_service_labels_adopts_labels_only_and_on_every_row_it_retargets(
    clients: ClientRegistry, tier3_writes: Tier3Writes
) -> None:
    """§10.5 (CMK-38599) at the REST boundary, with the `unchanged` row as the control.

    Two halves, and only the first is intended. The mode takes new *labels* and leaves parameters
    alone -- correct, and the reason it is not simply `new` under another name. But it applies that
    to every row it retargets, so an undecided service is silently adopted and a vanished one
    written back, on a host where the caller asked for nothing of the sort. The `unchanged` row is
    the tell: it is the one row already at the target, so it is the one row left untouched.

    When CMK-38599 lands, the payload does **not** shrink to the `changed` row -- the write is a
    full rebuild of the file (§1), so it still carries the whole baseline. What changes is which
    rows the mode *touched*: `new` drops out of the payload because it is no longer adopted, and
    `vanished` stays in it but with its **old** labels. Only `changed` should still carry
    `TIER3_NEW_LABELS`.
    """
    clients.ServiceDiscovery.start_service_discovery(str(TIER3_HOST), "only_service_labels")

    for source in ("changed", "new", "vanished"):
        entry = tier3_writes.written(tier3_service(source))
        assert entry.parameters == TIER3_OLD_PARAMS, source
        assert entry.service_labels == TIER3_NEW_LABELS, source

    untouched = tier3_writes.written(tier3_service("unchanged"))
    assert untouched.service_labels == TIER3_OLD_LABELS


# --- T3.5 / §6.2: the two modes that start a background job ----------------------------------


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
@pytest.mark.parametrize("mode", ("refresh", "tabula_rasa"))
def test_refresh_and_tabula_rasa_redirect(
    clients: ClientRegistry, tier3_writes: Tier3Writes, mode: str
) -> None:
    """The scanning modes answer `303` to `wait-for-completion` instead of a result body.

    The redirect is the whole contract for these two: a client that follows it gets the result of
    the job, and a client that does not gets no body at all.

    Neither reaches `set_autochecks_v2`, but that on its own says nothing -- they never could,
    because they write through `local_discovery` instead, and this tier patches that too. The
    assertion that separates them is which of them starts a rediscovery: `tabula_rasa` does, with
    every `DiscoverySettings` flag set, and `refresh` does not. That is the real asymmetry between
    the two modes and is otherwise unpinned at this tier.
    """
    resp = clients.ServiceDiscovery.start_service_discovery(str(TIER3_HOST), mode)

    resp.assert_status_code(303)
    assert resp.headers["Location"].endswith(
        f"/objects/service_discovery_run/{TIER3_HOST}/actions/wait-for-completion/invoke"
    )
    assert tier3_writes.services == []
    assert tier3_writes.scans == (
        [
            DiscoverySettings(
                update_host_labels=True,
                add_new_services=True,
                remove_vanished_services=True,
                update_changed_service_labels=True,
                update_changed_service_parameters=True,
            )
        ]
        if mode == "tabula_rasa"
        else []
    )


# --- T3.2 / §5.2, §10.1, §10.3: the seventeen accepted target phases -------------------------

#: Every value `target_phase` accepts, taken from the request model rather than listed, so that
#: adding one without deciding what it does fails here.
_TARGET_PHASES: tuple[str, ...] = tuple(
    sorted(get_args(get_type_hints(UpdateDiscoveryPhaseModel)["target_phase"]))
)

# `get_type_hints` rather than `__annotations__`, and the assertion rather than trusting it: a
# `from __future__ import annotations` in the model's module would turn the annotation into a
# string and `get_args` into `()`, silently reducing T3.2's parametrization to nothing instead of
# failing. That exact import was removed from `services.py` by abe88d592e9, so it is live churn in
# this repo rather than a hypothetical.
assert _TARGET_PHASES, "target_phase is no longer a readable Literal"

#: The two phases that name the source they are applied to, per source: asking for the phase a
#: service is already in computes no transition at all, so nothing is written.
_NO_OP_PHASE = {"unchanged": "monitored", "vanished": "vanished"}

#: The one phase per source that is a legitimate command and changes the file.
_COMMAND_PHASE = {"unchanged": "ignored", "vanished": "removed"}


def test_the_request_model_and_the_phase_map_accept_the_same_seventeen_phases() -> None:
    """The vocabulary is spelled out twice, and the two spellings must not drift.

    `UpdateDiscoveryPhaseModel.target_phase` is what the generated documentation offers a client
    and what the framework validates against; `SERVICE_DISCOVERY_PHASES` is what the handler can
    translate. A phase in the model but not the map would reach the handler and raise `KeyError`.
    """
    assert set(_TARGET_PHASES) == set(SERVICE_DISCOVERY_PHASES)
    assert len(_TARGET_PHASES) == 17


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
def test_update_service_phase_rejects_an_unknown_phase(
    clients: ClientRegistry, tier3_writes: Tier3Writes
) -> None:
    """A phase outside the seventeen is a `400` from the model, before the handler runs."""
    resp = clients.ServiceDiscovery.update_service_phase(
        str(TIER3_HOST),
        check_type=TIER3_PLUGIN,
        service_item="/unchanged",
        target_phase="nonsense",
        expect_ok=False,
    )

    resp.assert_status_code(400)
    assert resp.json["fields"]["body.target_phase"]["type"] == "literal_error"
    assert tier3_writes.services == []


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
@pytest.mark.parametrize(
    "host_name, check_type, service_item, expected_status",
    (
        (str(TIER3_HOST), "nonexistent_plugin", "/unchanged", 204),
        (str(TIER3_HOST), TIER3_PLUGIN, "/does-not-exist", 204),
        (str(TIER3_HOST), "nonexistent_plugin", None, 204),
        ("no.such.host", TIER3_PLUGIN, "/unchanged", 404),
    ),
    ids=["unknown-plugin", "unknown-item", "unknown-plugin-and-item", "unknown-host"],
)
def test_update_service_phase_reports_success_for_a_service_that_does_not_exist(
    clients: ClientRegistry,
    tier3_writes: Tier3Writes,
    host_name: str,
    check_type: str,
    service_item: str | None,
    expected_status: int,
) -> None:
    """Today: a phase change for a service not in the table is `204`; for a host, it is `404`.

    The last case is the contrast that makes the first three a defect rather than a convention.
    This endpoint names the thing to change with two identifiers, and treats "it does not exist"
    as an error for one and as success for the other: the host is checked by the path parameter's
    `HostConverter` before the handler runs, and the service is checked nowhere. So the endpoint
    already knows how to answer this question.

    For a service, `selected_services` matches nothing, `_get_table_target` returns each row's own
    source, `apply_changes` stays false, `compute_discovery_transition` returns `None`, and the
    endpoint reports success having written nothing -- no autochecks automation and no pending
    change, so no audit-log entry either. A client cannot tell it apart from a change that was
    made.

    This tier is the only place the answer is visible: below the endpoint, "the transition produced
    nothing" is the honest result, and it is the mapping to `204` that turns it into a claim of
    success. Same shape as §10.18 but a different cause, and §10.18's proposed
    `check_table_created` precondition would not catch it -- the table is fresh, the service is
    simply not in it.

    §10.19, low priority. When it lands the first three cases become `404` and the fourth is
    unchanged.
    """
    resp = clients.ServiceDiscovery.update_service_phase(
        host_name,
        check_type=check_type,
        service_item=service_item,
        target_phase="ignored",
        expect_ok=False,
    )

    resp.assert_status_code(expected_status)
    if expected_status == 404:
        # Not just any 404: the contrast this test rests on is that the *host* is validated, by the
        # path parameter's converter, before the handler runs. Asserting the field pins that.
        assert "path.host_name" in resp.json["fields"]
    assert tier3_writes.services == []


@pytest.mark.usefixtures("with_host", "inline_background_jobs")
@pytest.mark.parametrize("source", ("unchanged", "vanished"))
@pytest.mark.parametrize("phase", _TARGET_PHASES)
def test_update_service_phase_target_matrix(
    clients: ClientRegistry, tier3_writes: Tier3Writes, phase: str, source: str
) -> None:
    """§5.2 / A2-F1 / A2-F6: all seventeen phases are accepted with `204`, for both sources.

    Three outcomes per source, and which of the three a phase lands in is the finding:

    * the phase naming the source is a no-op -- no write at all;
    * one phase is a real command and changes the file;
    * the remaining fifteen are neither, and what they do depends on the source. From `unchanged`
      they **delete** the service. From `vanished` the same fifteen **keep** it. One
      `target_phase`, two opposite effects, chosen by a source the caller never sent: that is the
      pair-validity gap of A2-F6, and it is the reason the fix has to reject the pair rather than
      the value.

    **Which ticket owns which cell**, because every one of them flips an expectation below:

    * §10.3 / CMK-38588 owns the thirteen phases that name a state no caller can ask for. From
      `unchanged` twelve of them delete plus `undecided` and `removed`, which legitimately drop
      the service; from `vanished` twelve of them keep it (`vanished` itself is that source's
      no-op).
    * §10.1 / CMK-38587 owns `unchanged`/`ignored`: disabling a monitored service leaves it in the
      autochecks file, where the file should no longer mention it at all.
    * §10.16 / CMK-38592 owns three cells in the `vanished` column -- `ignored`, `undecided` and
      `monitored`. A vanished service accepts only `removed`; the other three name states the
      classifier cannot produce for a service that is no longer discovered, and §10.16's own table
      lists exactly these three REST targets as "each returning 204". Note this tier sees only
      half of that symptom: `_case_vanished` adds a **disabled-services rule** as well as writing
      the entry back, and the ruleset save is invisible here because the fixture records only
      `set_autochecks_v2`. The strict-xfail pair for it is Tier 1b's `vanished+disable`
      Divergence row.
    """
    # expect_ok=False deliberately: §10.3's and §10.16's fixes answer 400 here, and the raised
    # client error would replace "expected 204, got 400" with a request dump.
    resp = clients.ServiceDiscovery.update_service_phase(
        str(TIER3_HOST),
        check_type=TIER3_PLUGIN,
        service_item=f"/{source}",
        target_phase=phase,
        expect_ok=False,
    )
    resp.assert_status_code(204)

    if phase == _NO_OP_PHASE[source]:
        expected: list[frozenset[str]] = []
    elif phase == _COMMAND_PHASE[source]:
        expected = [
            TIER3_BASELINE if source == "unchanged" else TIER3_BASELINE - {tier3_service(source)}
        ]
    else:
        expected = [
            TIER3_BASELINE - {tier3_service("unchanged")}
            if source == "unchanged"
            else TIER3_BASELINE
        ]
    assert tier3_writes.services == expected


# --- T3.3 / §5.1, §10.4, §10.6: which permission actually stops a request ---------------------


@pytest.fixture(name="denied_permission")
def fixture_denied_permission(clients: ClientRegistry) -> Callable[[str], None]:
    """Log the client in as a user whose role is an admin minus one permission.

    A cloned role rather than the built-in `user` role: the point is to isolate a single
    permission, and every other difference between roles would be a second variable.
    """

    def deny(permission: str) -> None:
        clients.UserRole.clone(body={"role_id": "admin"})
        clients.UserRole.edit(role_id="adminx", body={"new_permissions": {permission: "no"}})
        clients.User.create(
            username="restricted",
            fullname="restricted",
            customer=None,
            roles=["adminx"],
            auth_option={"auth_type": "password", "password": "supersecretish"},
        )
        clients.HostConfig.create(host_name=str(TIER3_HOST), folder="/")
        clients.ServiceDiscovery.set_credentials("restricted", "supersecretish")

    return deny


@pytest.mark.usefixtures("inline_background_jobs")
@pytest.mark.parametrize(
    "permission",
    (
        "wato.service_discovery_to_monitored",
        "wato.service_discovery_to_ignored",
        "wato.service_discovery_to_undecided",
        "wato.service_discovery_to_removed",
    ),
)
def test_update_service_phase_demands_all_four_transition_permissions(
    clients: ClientRegistry,
    tier3_writes: Tier3Writes,
    denied_permission: Callable[[str], None],
    permission: str,
) -> None:
    """§5.1: the handler demands all four unconditionally, before knowing what was asked for.

    The request asks a monitored service to become monitored -- the no-op cell of T3.2. It writes
    nothing, and `Discovery._verify_permissions` demands nothing for it either, because that guard
    only fires when the row's source and target differ. So the four blanket `need_permission` calls
    in the handler are the *only* permission checks this request makes, and denying any one of them
    is what refuses it. Asking for `ignored` instead would leave the `to_ignored` case ambiguous:
    the transition would demand that one anyway, and the case would stay green under a fix that
    removed the blanket calls -- which a mutation run confirmed.

    Coarse in the safe direction, unlike the two permissions in the next test.
    """
    denied_permission(permission)

    clients.ServiceDiscovery.update_service_phase(
        str(TIER3_HOST),
        check_type=TIER3_PLUGIN,
        service_item="/unchanged",
        target_phase="monitored",
        expect_ok=False,
    ).assert_status_code(403)

    assert tier3_writes.services == []


@pytest.mark.usefixtures("inline_background_jobs")
@pytest.mark.parametrize("permission", ("wato.services", "wato.edit"))
def test_update_service_phase_writes_without_manage_services_or_edit_hosts(
    clients: ClientRegistry,
    tier3_writes: Tier3Writes,
    denied_permission: Callable[[str], None],
    permission: str,
) -> None:
    """§10.4 (CMK-38594): a role denied "Manage services" disables a service through the API.

    The same write is refused a `403` when it is asked for through `.../service_discovery_run`,
    which demands `wato.edit` in its handler and `wato.services` on entry to `perform_fix_all`,
    inside `_service_discovery_context`. (Not in its pre-gate:
    `has_discovery_action_specific_permissions` only ever looks at the four `to_*` permissions --
    T3.3b is about that distinction.) Only this endpoint demands neither, so the permission a
    client needs depends on which endpoint it happens to use. Tier 2 owns this ticket's tripwire -- on the permissions the endpoint
    *declares*, which is the one observation point no fix can avoid changing
    (`test_services_dispatch.py`, T2.12). This test is the end-to-end symptom: when CMK-38594
    lands, the expectation here becomes `403`.
    """
    denied_permission(permission)

    # expect_ok=False deliberately: when CMK-38594 lands this answers 403, and the client would
    # otherwise raise on the response before `assert_status_code` could report the status.
    clients.ServiceDiscovery.update_service_phase(
        str(TIER3_HOST),
        check_type=TIER3_PLUGIN,
        service_item="/unchanged",
        target_phase="ignored",
        expect_ok=False,
    ).assert_status_code(204)

    assert tier3_writes.services == [TIER3_BASELINE]
    clients.ServiceDiscovery.start_service_discovery(
        str(TIER3_HOST), "fix_all", expect_ok=False
    ).assert_status_code(403)


@pytest.mark.usefixtures("inline_background_jobs")
def test_the_discovery_pre_gate_and_the_transition_refuse_with_different_messages(
    clients: ClientRegistry,
    tier3_writes: Tier3Writes,
    denied_permission: Callable[[str], None],
) -> None:
    """§10.6: `has_discovery_action_specific_permissions` does not agree with what is demanded.

    Both modes below end in `403` for a role denied `to_monitored`, but by different routes, and
    the message says which. `fix_all` is pre-gated on `to_monitored ∧ to_removed`, so the endpoint
    refuses before reading anything. `only_service_labels` is pre-gated on `wato.services` alone
    and demands `to_monitored` inside the transition, so the refusal comes from the permission
    machinery after the check table has been fetched. Neither writes anything -- every permission
    check runs inside the pure transition, before the first write -- which is what keeps §10.6 a
    requirement for the rewrite rather than a defect with a data consequence.
    """
    denied_permission("wato.service_discovery_to_monitored")

    pre_gate = clients.ServiceDiscovery.start_service_discovery(
        str(TIER3_HOST), "fix_all", expect_ok=False
    )
    pre_gate.assert_status_code(403)
    assert pre_gate.json["detail"] == (
        "You do not have the necessary permissions to execute this action"
    )

    demanded = clients.ServiceDiscovery.start_service_discovery(
        str(TIER3_HOST), "only_service_labels", expect_ok=False
    )
    demanded.assert_status_code(403)
    assert "Move to monitored services" in demanded.json["detail"]

    assert tier3_writes.services == []


# --- T3.4 and T3.6 / §6.2, §10.18: a request issued while a scan is running -------------------
#
# The two endpoints disagree, and the disagreement is the finding. T3.6 has no `xfail` partner:
# §10.18's fix answers `409` for a request that carries a `check_table_created` precondition, a
# field the request model does not have yet, so an xfail written now could only send a request
# without it and would go on failing -- silently -- after a correct fix. It needs no partner
# either. The status code below is the assertion the fix changes, so it cannot land without
# turning this file red, which is exactly what a tripwire is for.


@pytest.fixture(name="job_running")
def fixture_job_running(mocker: MockerFixture) -> None:
    mocker.patch.object(ServiceDiscoveryBackgroundJob, "is_active", return_value=True)


@pytest.mark.usefixtures("with_host", "inline_background_jobs", "job_running")
def test_execute_discovery_conflicts_with_running_job(
    clients: ClientRegistry, tier3_writes: Tier3Writes
) -> None:
    """T3.4: starting a discovery while one is running is refused."""
    resp = clients.ServiceDiscovery.start_service_discovery(
        str(TIER3_HOST), "fix_all", expect_ok=False
    )

    resp.assert_status_code(409)
    assert resp.json["detail"] == "A service discovery background job is currently running"
    assert tier3_writes.services == []


@pytest.mark.usefixtures("with_host", "inline_background_jobs", "job_running")
def test_update_service_phase_during_active_job(
    clients: ClientRegistry, tier3_writes: Tier3Writes
) -> None:
    """§10.18 (CMK-38598): the same conflict, through the other endpoint, reports success.

    `update_service_phase` never probes the job. While one runs, the check table it reads is the
    empty one this process built in `__init__` -- the job's snapshot lives in the job's process --
    so the transition finds nothing to change, returns `None`, and the endpoint answers
    `204 No Content` having written nothing. A client that starts a `refresh` without waiting for
    `wait-for-completion` and then sets phases loses those calls and is told they succeeded.

    Nothing is corrupted: the guard that stops an empty table from being rebuilt into an empty
    autochecks file is what makes the write a no-op rather than a deletion. When CMK-38598 lands,
    the expectation here becomes `409` and the request has to carry `check_table_created`.
    """
    # expect_ok=False deliberately: when CMK-38598 lands this answers 409 (see the note above the
    # section), and the raised client error would hide which status came back.
    clients.ServiceDiscovery.update_service_phase(
        str(TIER3_HOST),
        check_type=TIER3_PLUGIN,
        service_item="/unchanged",
        target_phase="ignored",
        expect_ok=False,
    ).assert_status_code(204)

    assert tier3_writes.services == []
