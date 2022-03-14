#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import itertools
from typing import Any, Dict, List, NamedTuple, Optional

import pytest

from tests.testlib import on_time

from cmk.base.plugins.agent_based import ps_section
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.utils import ps as ps_utils


def splitter(
    text: str,
    split_symbol: Optional[str] = None,
) -> List[List[str]]:
    return [line.split(split_symbol) for line in text.split("\n")]


def generate_inputs() -> List[List[List[str]]]:
    return [
        # CMK 1.5
        # linux, openwrt agent(5 entry, cmk>=1.2.7)
        # NOTE: It is important that the last line ("(twelve,...")
        #       remains the last line of the following output!
        splitter(
            """(root,225948,9684,00:00:03/05:05:29,1) /sbin/init splash
(root,0,0,00:00:00/05:05:29,2) [kthreadd]
(on,288260,7240,00:00:00/05:03:00,4480) /usr/bin/gnome-keyring-daemon --start --foreground --components=secrets
(on,1039012,11656,00:00:00/05:02:41,5043) /usr/bin/pulseaudio --start --log-target=syslog
(on,1050360,303252,00:14:59/1-03:59:39,9902) emacs
(on,2924232,472252,00:12:05/07:24:15,7912) /usr/lib/firefox/firefox
(heute,11180,1144,00:00:00/03:54:10,10884) /omd/sites/heute/lib/cmc/checkhelper
(twelve,11180,1244,00:00:00/02:37:39,30136) /omd/sites/twelve/lib/cmc/checkhelper"""
        ),
        # solaris (5 entry cmk>=1.5)
        splitter(
            """(root,4056,1512,0.0/52-04:56:05,5689) /usr/lib/ssh/sshd
(zombie,0,0,-/-,1952) <defunct>
(zombie,0,0,-/-,3952)
(zombie,0,0,-/-,4952) """
        ),
        # windows agent
        splitter(
            """(SYSTEM,0,0,0,0,0,0,0,0,1,0)	System Idle Process
(\\NT AUTHORITY\\SYSTEM,46640,10680,0,600,5212,27924179,58500375,370,11,12)	svchost.exe
(\\NT AUTHORITY\\NETWORK SERVICE,36792,10040,0,676,5588,492183155,189541215,380,8,50)	svchost.exe
(\\NT AUTHORITY\\LOCAL SERVICE,56100,18796,0,764,56632,1422261117,618855967,454,13,4300)	svchost.exe
(\\KLAPPRECHNER\\ab,29284,2948,0,3124,904,400576,901296,35,1,642)\tNOTEPAD.EXE""",
            "\t",
        ),
        # aix, bsd, hpux, macos, netbsd, openbsd agent(4 entry, cmk>=1.1.5)
        splitter("(db2prtl,17176,17540,0.0) /usr/lib/ssh/sshd"),
        # aix with zombies
        splitter(
            """(oracle,9588,298788,0.0) ora_dmon_uc4prd
(<defunct>,,,)
(oracle,11448,300648,0.0) oraclemetroprd (LOCAL=NO)"""
        ),
        # windows agent(10 entry, cmk>1.2.5)
        splitter(
            """(SYSTEM,0,0,0,0,0,0,0,0,2)	System Idle Process
(\\KLAPPRECHNER\\ab,29284,2948,0,3124,904,400576,901296,35,1)\tNOTEPAD.EXE""",
            "\t",
        ),
        # windows agent(wmic_info, cmk<1.2.5)# From server-windows-mssql-2
        splitter(
            """[System Process]
System
System Idle Process
smss.exe
csrss.exe
csrss.exe""",
            "\0",
        )
        + splitter(
            """[wmic process]
Node,HandleCount,KernelModeTime,Name,PageFileUsage,ProcessId,ThreadCount,UserModeTime,VirtualSize,WorkingSetSize
WSOPREKPFS01,0,388621186093750,System Idle Process,0,0,24,0,65536,24576
WSOPREKPFS01,1227,368895625000,System,132,4,273,0,14831616,10862592
WSOPREKPFS01,53,2031250,smss.exe,360,520,2,156250,4685824,323584
WSOPREKPFS01,679,10051718750,csrss.exe,2640,680,10,2222031250,70144000,2916352
WSOPREKPFS01,85,126562500,csrss.exe,1176,744,8,468750,44486656,569344
[wmic process end]""",
            ",",
        ),
        # Second Generation
        splitter(
            "(root) /usr/sbin/xinetd -pidfile /var/run/xinetd.pid -stayalive -inetd_compat -inetd_ipv6"
        ),
        # First Generation
        splitter(
            "/usr/sbin/xinetd -pidfile /var/run/xinetd.pid -stayalive -inetd_compat -inetd_ipv6"
        ),
    ]


PS_DISCOVERY_WATO_RULES = [
    {
        "default_params": {"cpu_rescale_max": "cpu_rescale_max_unspecified"},
        "descr": "smss",
        "match": "~smss.exe",
    },
    {
        "default_params": {
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "cpulevels": (90.0, 98.0),
            "handle_count": (1000, 2000),
            "levels": (1, 1, 99999, 99999),
            "max_age": (3600, 7200),
            "resident_levels": (104857600, 209715200),
            "resident_levels_perc": (25.0, 50.0),
            "single_cpulevels": (90.0, 98.0),
            "virtual_levels": (1073741824000, 2147483648000),
        },
        "descr": "svchost",
        "match": "svchost.exe",
    },
    {
        "default_params": {
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "process_info": "text",
        },
        "match": "~.*(fire)fox",
        "descr": "firefox is on %s",
        "user": None,
    },
    {
        "default_params": {
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "process_info": "text",
        },
        "match": "~.*(fire)fox",
        "descr": "firefox is on %s",
        "user": None,
        "label": {"marco": "polo", "peter": "pan"},
    },
    {
        "default_params": {
            "cpu_rescale_max": True,
            "cpu_average": 15,
            "process_info": "html",
            "resident_levels_perc": (25.0, 50.0),
            "virtual_levels": (1024**3, 2 * 1024**3),
            "resident_levels": (1024**3, 2 * 1024**3),
            "icon": "emacs.png",
        },
        "descr": "emacs %u",
        "match": "emacs",
        "user": False,
    },
    {
        "default_params": {
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "max_age": (3600, 7200),
            "resident_levels_perc": (25.0, 50.0),
            "single_cpulevels": (90.0, 98.0),
            "resident_levels": (104857600, 209715200),
        },
        "match": "~.*cron",
        "descr": "cron",
        "user": "root",
    },
    {
        "default_params": {"cpu_rescale_max": "cpu_rescale_max_unspecified"},
        "descr": "sshd",
        "match": "~.*sshd",
    },
    {
        "default_params": {"cpu_rescale_max": "cpu_rescale_max_unspecified"},
        "descr": "PS counter",
        "user": "zombie",
    },
    {
        "default_params": {
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "process_info": "text",
        },
        "match": r"~/omd/sites/(\w+)/lib/cmc/checkhelper",
        "descr": "Checkhelpers %s",
        "user": None,
    },
    {
        "default_params": {
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "process_info": "text",
        },
        "match": r"~/omd/sites/\w+/lib/cmc/checkhelper",
        "descr": "Checkhelpers Overall",
        "user": None,
    },
    {},
]

PS_DISCOVERED_ITEMS = [
    Service(
        item="emacs on",
        parameters={
            "cpu_average": 15,
            "cpu_rescale_max": True,
            "resident_levels_perc": (25.0, 50.0),
            "process": "emacs",
            "icon": "emacs.png",
            "user": "on",
            "process_info": "html",
            "virtual_levels": (1024**3, 2 * 1024**3),
            "resident_levels": (1024**3, 2 * 1024**3),
            "match_groups": (),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="firefox is on fire",
        parameters={
            "process": "~.*(fire)fox",
            "process_info": "text",
            "user": None,
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "match_groups": ("fire",),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="Checkhelpers heute",
        parameters={
            "process": "~/omd/sites/(\\w+)/lib/cmc/checkhelper",
            "process_info": "text",
            "user": None,
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "match_groups": ("heute",),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="Checkhelpers Overall",
        parameters={
            "process": "~/omd/sites/\\w+/lib/cmc/checkhelper",
            "process_info": "text",
            "user": None,
            "match_groups": (),
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "cgroup": (None, False),
        },
    ),
    Service(
        item="Checkhelpers twelve",
        parameters={
            "process": "~/omd/sites/(\\w+)/lib/cmc/checkhelper",
            "process_info": "text",
            "user": None,
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "match_groups": ("twelve",),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="sshd",
        parameters={
            "process": "~.*sshd",
            "user": None,
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "match_groups": (),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="PS counter",
        parameters={
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "process": None,
            "user": "zombie",
            "match_groups": (),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="svchost",
        parameters={
            "cpulevels": (90.0, 98.0),
            "handle_count": (1000, 2000),
            "levels": (1, 1, 99999, 99999),
            "max_age": (3600, 7200),
            "process": "svchost.exe",
            "resident_levels": (104857600, 209715200),
            "resident_levels_perc": (25.0, 50.0),
            "single_cpulevels": (90.0, 98.0),
            "user": None,
            "virtual_levels": (1073741824000, 2147483648000),
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "match_groups": (),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="smss",
        parameters={
            "process": "~smss.exe",
            "user": None,
            "cpu_rescale_max": "cpu_rescale_max_unspecified",
            "match_groups": (),
            "cgroup": (None, False),
        },
    ),
]


def test_inventory_common():
    info = list(itertools.chain.from_iterable(generate_inputs()))
    assert sorted(
        {
            s.item: s
            for s in ps_utils.discover_ps(  # type: ignore[attr-defined]
                PS_DISCOVERY_WATO_RULES,  # type: ignore[arg-type]
                ps_section.parse_ps(info),
                None,
                None,
                None,
            )
        }.values(),
        key=lambda s: s.item or "",
    ) == sorted(
        PS_DISCOVERED_ITEMS, key=lambda s: s.item or ""
    )  # type: ignore[attr-defined]


CheckResult = tuple

check_results = [
    [
        Result(
            state=state.OK,
            summary="Processes: 1",
        ),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Result(
            state=state.WARN,
            summary="virtual: 1.00 GiB (warn/crit at 1.00 GiB/2.00 GiB)",
        ),
        Metric("vsz", 1050360, levels=(1073741824, 2147483648)),
        Result(
            state=state.OK,
            summary="physical: 296 MiB",
        ),
        Metric("rss", 303252, levels=(1073741824, 2147483648)),
        Result(
            state=state.WARN,
            summary="Percentage of total RAM: 28.92% (warn/crit at 25.00%/50.00%)",
        ),
        Metric("pcpu", 0.0),
        Metric("pcpuavg", 0.0, boundaries=(0, 15)),
        Result(
            state=state.OK,
            summary="CPU: 0%, 15 min average: 0%",
        ),
        Result(
            state=state.OK,
            summary="Running for: 1 day 3 hours",
        ),
        Result(
            state=state.OK,
            notice=(
                "<table><tr><th>name</th><th>user</th><th>virtual size</th>"
                "<th>resident size</th><th>creation time</th><th>pid</th><th>cpu usage</th></tr>"
                "<tr><td>emacs</td><td>on</td><td>1.00 GiB</td><td>296 MiB</td>"
                "<td>Oct 23 2018 08:02:43</td><td>9902</td><td>0.0%</td></tr></table>"
            ),
        ),
    ],
    [
        Result(
            state=state.OK,
            summary="Processes: 1",
        ),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Result(
            state=state.OK,
            summary="virtual: 2.79 GiB",
        ),
        Metric("vsz", 2924232),
        Result(
            state=state.OK,
            summary="physical: 461 MiB",
        ),
        Metric("rss", 472252),
        Metric("pcpu", 0.0),
        Result(state=state.OK, summary="CPU: 0%"),
        Result(state=state.OK, summary="Running for: 7 hours 24 minutes"),
        Result(
            state=state.OK,
            notice=(
                "name /usr/lib/firefox/firefox, user on, virtual size 2.79 GiB,"
                " resident size 461 MiB, creation time Oct 24 2018 04:38:07, pid 7912,"
                " cpu usage 0.0%\r\n"
            ),
        ),
    ],
    [
        Result(state=state.OK, summary="Processes: 1"),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=state.OK, summary="virtual: 10.9 MiB"),
        Metric("vsz", 11180),
        Result(state=state.OK, summary="physical: 1.12 MiB"),
        Metric("rss", 1144),
        Metric("pcpu", 0.0),
        Result(state=state.OK, summary="CPU: 0%"),
        Result(state=state.OK, summary="Running for: 3 hours 54 minutes"),
        Result(
            state=state.OK,
            notice=(
                "name /omd/sites/heute/lib/cmc/checkhelper, user heute, virtual size 10.9 MiB,"
                " resident size 1.12 MiB, creation time Oct 24 2018 08:08:12, pid 10884,"
                " cpu usage 0.0%\r\n"
            ),
        ),
    ],
    [
        Result(state=state.OK, summary="Processes: 2"),
        Metric("count", 2, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=state.OK, summary="virtual: 21.8 MiB"),
        Metric("vsz", 22360),
        Result(state=state.OK, summary="physical: 2.33 MiB"),
        Metric("rss", 2388),
        Metric("pcpu", 0.0),
        Result(state=state.OK, summary="CPU: 0%"),
        Result(state=state.OK, summary="Youngest running for: 2 hours 37 minutes"),
        Metric("age_youngest", 9459.0),
        Result(state=state.OK, summary="Oldest running for: 3 hours 54 minutes"),
        Metric("age_oldest", 14050.0),
        Result(
            state=state.OK,
            notice=(
                "name /omd/sites/heute/lib/cmc/checkhelper, user heute, virtual size 10.9 MiB,"
                " resident size 1.12 MiB, creation time Oct 24 2018 08:08:12, pid 10884,"
                " cpu usage 0.0%\r\nname /omd/sites/twelve/lib/cmc/checkhelper, user twelve,"
                " virtual size 10.9 MiB, resident size 1.21 MiB, creation time Oct 24 2018 09:24:43, "
                "pid 30136, cpu usage 0.0%\r\n"
            ),
        ),
    ],
    [
        Result(state=state.OK, summary="Processes: 1"),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=state.OK, summary="virtual: 10.9 MiB"),
        Metric("vsz", 11180),
        Result(state=state.OK, summary="physical: 1.21 MiB"),
        Metric("rss", 1244),
        Metric("pcpu", 0.0),
        Result(state=state.OK, summary="CPU: 0%"),
        Result(state=state.OK, summary="Running for: 2 hours 37 minutes"),
        Result(
            state=state.OK,
            notice=(
                "name /omd/sites/twelve/lib/cmc/checkhelper, user twelve, virtual size 10.9 MiB,"
                " resident size 1.21 MiB, creation time Oct 24 2018 09:24:43, pid 30136,"
                " cpu usage 0.0%\r\n"
            ),
        ),
    ],
    [
        Result(state=state.OK, summary="Processes: 2"),
        Metric("count", 2, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=state.OK, summary="virtual: 20.7 MiB"),
        Metric("vsz", 21232),
        Result(state=state.OK, summary="physical: 18.6 MiB"),
        Metric("rss", 19052),
        Metric("pcpu", 0.0),
        Result(state=state.OK, summary="CPU: 0%"),
        Result(state=state.OK, summary="Running for: 52 days 4 hours"),
    ],
    [
        Result(state=state.OK, summary="Processes: 1"),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Metric("pcpu", 0.0),
        Result(state=state.OK, summary="CPU: 0%"),
        Result(state=state.OK, summary="Running for: 0 seconds"),
    ],
    [
        Result(state=state.OK, summary="Processes: 3"),
        Metric("count", 3, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=state.OK, summary="virtual: 136 MiB"),
        Metric("vsz", 139532, levels=(1073741824000, 2147483648000)),
        Result(state=state.OK, summary="physical: 38.6 MiB"),
        Metric("rss", 39516, levels=(104857600, 209715200)),
        Result(
            state=state.UNKNOWN,
            summary="Percentual RAM levels configured, but total RAM is unknown",
        ),
        Metric("pcpu", 0.0, levels=(90.0, 98.0)),
        Result(state=state.OK, summary="CPU: 0%"),
        Result(
            state=state.OK,
            notice="svchost.exe with PID 600 CPU: 0%",
        ),
        Result(
            state=state.OK,
            notice="svchost.exe with PID 676 CPU: 0%",
        ),
        Result(
            state=state.OK,
            notice="svchost.exe with PID 764 CPU: 0%",
        ),
        Result(
            state=state.WARN,
            summary="Process handles: 1204 (warn/crit at 1000/2000)",
        ),
        Metric("process_handles", 1204, levels=(1000, 2000)),
        Result(state=state.OK, summary="Youngest running for: 12 seconds"),
        Metric("age_youngest", 12.0),
        Result(
            state=state.WARN,
            summary=(
                "Oldest running for: 1 hour 11 minutes"
                " (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)"
            ),
        ),
        Metric("age_oldest", 4300.0, levels=(3600.0, 7200.0)),
    ],
    [
        Result(state=state.OK, summary="Processes: 1"),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=state.OK, summary="virtual: 4.47 MiB"),
        Metric("vsz", 4576),
        Result(state=state.OK, summary="physical: 316 KiB"),
        Metric("rss", 316),
        Metric("pcpu", 0.0),
        Result(state=state.OK, summary="CPU: 0%"),
        Result(state=state.OK, summary="Process handles: 53"),
        Metric("process_handles", 53),
    ],
]


@pytest.mark.parametrize(
    "inv_item, reference",
    list(zip(PS_DISCOVERED_ITEMS, check_results)),
    ids=[s.item for s in PS_DISCOVERED_ITEMS],
)
def test_check_ps_common(inv_item, reference):
    parsed: List = []
    for info in generate_inputs():
        _cpu_cores, data = ps_section.parse_ps(info)
        parsed.extend((None, ps_info, cmd_line) for (ps_info, cmd_line) in data)

    with on_time(1540375342, "CET"):
        factory_defaults = {"levels": (1, 1, 99999, 99999)}
        factory_defaults.update(inv_item.parameters)
        test_result = list(
            ps_utils.check_ps_common(
                label="Processes",
                item=inv_item.item,
                params=factory_defaults,  # type: ignore[arg-type]
                process_lines=parsed,
                cpu_cores=1,
                total_ram_map={"": 1024**3} if "emacs" in inv_item.item else {},
            )
        )
        assert test_result == reference


class cpu_config(NamedTuple):
    name: str
    agent_info: str
    cputime: float
    cpu_cores: int
    exp_load: float
    cpu_rescale_max: Optional[bool]


cpu_util_data = [
    cpu_config(
        "linux no cpu scale conf 1 core",
        "(on,105,30,00:00:{:02}/03:59:39,902) test",
        30,
        1,
        50,
        None,
    ),
    cpu_config(
        "linux no cpu scale conf 2 cores",
        "(on,105,30,00:00:{:02}/03:59:39,902) test",
        30,
        2,
        50,
        None,
    ),
    cpu_config(
        "linux No_Core_division 2 cores",
        "(on,105,30,00:00:{:02}/03:59:39,902) test",
        120,
        2,
        200,
        False,
    ),
    cpu_config(
        "linux Core_division 2 cores", "(on,105,30,00:00:{:02}/03:59:39,902) test", 30, 2, 25, True
    ),
    cpu_config(
        "Win no cpu scale conf 2 cores",
        "(\\KLAPPRECHNER\ab,105,30,0,3124,904,{0}0000000,{0}0000000,0,1,14340) test.exe",
        54,
        2,
        90,
        None,
    ),
    cpu_config(
        "Win No_Core_division 2 cores",
        "(\\KLAPPRECHNER\ab,105,30,0,3124,904,{0}0000000,{0}0000000,0,1,14340) test.exe",
        54,
        2,
        180,
        False,
    ),
    cpu_config(
        "Win Core_division 2 cores",
        "(\\KLAPPRECHNER\ab,105,30,0,3124,904,{0}0000000,{0}0000000,0,1,14340) test.exe",
        54,
        2,
        90,
        True,
    ),
    cpu_config(
        "Solaris,BSD,etc no cpu conf 1 core",
        "(on,105,30,{}/03:59:39,902) test",
        30.8,
        1,
        30.8,
        None,
    ),
    cpu_config(
        "Solaris,BSD,etc no cpu conf 2 cores",
        "(on,105,30,{}/03:59:39,902) test",
        174.8,
        2,
        174.8,
        None,
    ),
    cpu_config(
        "Solaris,BSD,etc No_Core_division 2 cores",
        "(on,105,30,{}/03:59:39,902) test",
        174.8,
        2,
        174.8,
        False,
    ),
    cpu_config(
        "Solaris,BSD,etc Core_division 2 cores",
        "(on,105,30,{}/03:59:39,902) test",
        174.8,
        2,
        174.8 / 2,
        True,
    ),
]


@pytest.mark.parametrize("data", cpu_util_data, ids=[a.name for a in cpu_util_data])
def test_check_ps_common_cpu(data):
    def time_info(service, agent_info, check_time, cputime, cpu_cores):
        with on_time(datetime.datetime.utcfromtimestamp(check_time), "CET"):
            _cpu_info, parsed_lines = ps_section.parse_ps(splitter(agent_info.format(cputime)))
            lines_with_node_name = [
                (None, ps_info, cmd_line) for (ps_info, cmd_line) in parsed_lines
            ]

            return list(
                ps_utils.check_ps_common(
                    label="Processes",
                    item=service.item,
                    params=service.parameters,  # type: ignore[arg-type]
                    process_lines=lines_with_node_name,
                    cpu_cores=cpu_cores,
                    total_ram_map={},
                )
            )

    rescale_params = (
        {"cpu_rescale_max": data.cpu_rescale_max} if data.cpu_rescale_max is not None else {}
    )
    service = Service(
        item="test",
        parameters={
            "process": "~test",
            "user": None,
            "levels": (1, 1, 99999, 99999),  # from factory defaults
            **rescale_params,
        },
    )

    # Initialize counters
    time_info(service, data.agent_info, 0, 0, data.cpu_cores)
    # Check_cpu_utilization
    output = time_info(service, data.agent_info, 60, data.cputime, data.cpu_cores)

    assert output[:6] == [
        Result(state=state.OK, summary="Processes: 1"),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=state.OK, summary="virtual: 105 KiB"),
        Metric("vsz", 105),
        Result(state=state.OK, summary="physical: 30.0 KiB"),
        Metric("rss", 30),
    ]
    assert output[8:] == [
        Result(state=state.OK, summary="Running for: 3 hours 59 minutes"),
    ]


@pytest.mark.parametrize(
    "levels, reference",
    [
        (
            (1, 1, 99999, 99999),
            [
                Result(state=state.CRIT, summary="Processes: 0 (warn/crit below 1/1)"),
                Metric("count", 0, levels=(100000, 100000), boundaries=(0, None)),
            ],
        ),
        (
            (0, 0, 99999, 99999),
            [
                Result(state=state.OK, summary="Processes: 0"),
                Metric("count", 0, levels=(100000, 100000), boundaries=(0, None)),
            ],
        ),
    ],
)
def test_check_ps_common_count(levels, reference):
    _cpu_info, parsed_lines = ps_section.parse_ps(
        splitter("(on,105,30,00:00:{:02}/03:59:39,902) single")
    )
    lines_with_node_name = [(None, ps_info, cmd_line) for (ps_info, cmd_line) in parsed_lines]

    params = {
        "process": "~test",
        "user": None,
        "levels": levels,
    }

    output = list(
        ps_utils.check_ps_common(
            label="Processes",
            item="empty",
            params=params,  # type: ignore[arg-type]
            process_lines=lines_with_node_name,
            cpu_cores=1,
            total_ram_map={},
        )
    )
    assert output == reference


def test_subset_patterns():

    section_ps = ps_section.parse_ps(
        splitter(
            """(user,0,0,0.5) main
(user,0,0,0.4) main_dev
(user,0,0,0.1) main_dev
(user,0,0,0.5) main_test"""
        )
    )

    # Boundary in match is necessary otherwise main instance accumulates all
    inv_params: List[Dict] = [
        {
            "default_params": {"cpu_rescale_max": True, "levels": (1, 1, 99999, 99999)},
            "match": "~(main.*)\\b",
            "descr": "%s",
        },
        {},
    ]

    discovered = [
        Service(
            item="main",
            parameters={
                "cpu_rescale_max": True,
                "levels": (1, 1, 99999, 99999),
                "process": "~(main.*)\\b",
                "match_groups": ("main",),
                "user": None,
                "cgroup": (None, False),
            },
        ),
        Service(
            item="main_dev",
            parameters={
                "cpu_rescale_max": True,
                "levels": (1, 1, 99999, 99999),
                "process": "~(main.*)\\b",
                "match_groups": ("main_dev",),
                "user": None,
                "cgroup": (None, False),
            },
        ),
        Service(
            item="main_test",
            parameters={
                "cpu_rescale_max": True,
                "levels": (1, 1, 99999, 99999),
                "process": "~(main.*)\\b",
                "match_groups": ("main_test",),
                "user": None,
                "cgroup": (None, False),
            },
        ),
    ]

    test_discovered = ps_utils.discover_ps(
        inv_params, section_ps, None, None, None
    )  # type: ignore[arg-type]
    assert {s.item: s for s in test_discovered} == {
        s.item: s for s in discovered
    }  # type: ignore[attr-defined]

    for service, count in zip(discovered, [1, 2, 1]):
        assert isinstance(service.item, str)
        output = list(
            ps_utils.check_ps_common(
                label="Processes",
                item=service.item,
                params=service.parameters,  # type: ignore[arg-type]
                process_lines=[(None, psi, cmd_line) for (psi, cmd_line) in section_ps[1]],
                cpu_cores=1,
                total_ram_map={},
            )
        )
        assert output[0] == Result(state=state.OK, summary="Processes: %s" % count)


@pytest.mark.parametrize("cpu_cores", [2, 4, 5])
def test_cpu_util_single_process_levels(cpu_cores):
    """Test CPU utilization per single process.
    - Check that Number of cores weight is active
    - Check that single process CPU utilization is present only on warn/crit states"""

    params: Dict[str, Any] = {
        "process": "~.*firefox",
        "process_info": "text",
        "cpu_rescale_max": True,
        "levels": (1, 1, 99999, 99999),
        "single_cpulevels": (45.0, 80.0),
    }

    def run_check_ps_common_with_elapsed_time(check_time, cputime):
        with on_time(check_time, "CET"):
            agent_info = """(on,2275004,434008,00:00:49/26:58,25576) firefox
(on,1869920,359836,00:01:23/6:57,25664) firefox
(on,7962644,229660,00:00:10/26:56,25758) firefox
(on,1523536,83064,00:{:02}:00/26:55,25898) firefox"""
            _cpu_info, parsed_lines = ps_section.parse_ps(splitter(agent_info.format(cputime)))
            lines_with_node_name = [
                (None, ps_info, cmd_line) for (ps_info, cmd_line) in parsed_lines
            ]

            return list(
                ps_utils.check_ps_common(
                    label="Processes",
                    item="firefox",
                    params=params,  # type: ignore[arg-type]
                    process_lines=lines_with_node_name,
                    cpu_cores=cpu_cores,
                    total_ram_map={},
                )
            )

    # CPU utilization is a counter, initialize it
    run_check_ps_common_with_elapsed_time(0, 0)
    # CPU utilization is a counter, after 60s time, one process consumes 2 min of CPU
    output = run_check_ps_common_with_elapsed_time(60, 2)

    cpu_util = 200.0 / cpu_cores
    cpu_util_s = ps_utils.render.percent(cpu_util)
    single_msg = "firefox with PID 25898 CPU: %s (warn/crit at 45.00%%/80.00%%)" % cpu_util_s
    reference = [
        Result(state=state.OK, summary="Processes: 4"),
        Metric("count", 4, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=state.OK, summary="virtual: 13.0 GiB"),
        Metric("vsz", 13631104),
        Result(state=state.OK, summary="physical: 1.06 GiB"),
        Metric("rss", 1106568),
        Metric("pcpu", cpu_util),
        Result(state=state.OK, summary="CPU: %s" % cpu_util_s),
        Result(state=state.OK, notice="firefox with PID 25576 CPU: 0%"),
        Result(state=state.OK, notice="firefox with PID 25664 CPU: 0%"),
        Result(state=state.OK, notice="firefox with PID 25758 CPU: 0%"),
        Result(state=state.OK, notice="firefox with PID 25898 CPU: 40.00%"),
        Result(state=state.OK, summary="Youngest running for: 6 minutes 57 seconds"),
        Metric("age_youngest", 417.0),
        Result(state=state.OK, summary="Oldest running for: 26 minutes 58 seconds"),
        Metric("age_oldest", 1618.0),
        Result(
            state=state.OK,
            notice="\r\n".join(
                [
                    "name firefox, user on, virtual size 2.17 GiB, resident size 424 MiB,"
                    " creation time Jan 01 1970 00:34:02, pid 25576, cpu usage 0.0%",
                    "name firefox, user on, virtual size 1.78 GiB, resident size 351 MiB,"
                    " creation time Jan 01 1970 00:54:03, pid 25664, cpu usage 0.0%",
                    "name firefox, user on, virtual size 7.59 GiB, resident size 224 MiB,"
                    " creation time Jan 01 1970 00:34:04, pid 25758, cpu usage 0.0%",
                    "name firefox, user on, virtual size 1.45 GiB, resident size 81.1 MiB,"
                    " creation time Jan 01 1970 00:34:05, pid 25898, cpu usage %.1f%%\r\n"
                    % cpu_util,
                ]
            ),
        ),
    ]

    if cpu_util > params["single_cpulevels"][1]:
        reference[11] = Result(state=state.CRIT, summary=single_msg)
    elif cpu_util > params["single_cpulevels"][0]:
        reference[11] = Result(state=state.WARN, summary=single_msg)

    assert output == reference
