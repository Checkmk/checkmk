#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
import itertools
import time
from collections.abc import Sequence
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

import pytest
import time_machine
from pytest_mock import MockerFixture

from cmk.agent_based.v2 import Metric, render, Result, Service, State
from cmk.plugins.collection.agent_based import ps_check, ps_section
from cmk.plugins.lib import ps as ps_utils


def splitter(
    text: str,
    split_symbol: str | None = None,
) -> list[list[str]]:
    return [line.split(split_symbol) for line in text.split("\n")]


def generate_inputs() -> list[list[list[str]]]:
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
        "descr": "emacs %u - include_ram_map",
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
    {
        "default_params": {
            "cpulevels": (90.0, 98.0),
            "cpu_rescale_max": True,
        },
        "match": "~.*(fire)fox",
        "descr": "CPU levels total only",
        "user": None,
    },
    {
        "default_params": {
            "virtual_levels": (90.0, 98.0),
            "cpu_rescale_max": True,
        },
        "match": "~.*(fire)fox",
        "descr": "Virtual memory levels total only",
        "user": None,
    },
    {
        "default_params": {
            "resident_levels": (90.0, 98.0),
            "cpu_rescale_max": True,
        },
        "match": "~.*(fire)fox",
        "descr": "Resident memory levels total only",
        "user": None,
    },
    {
        "default_params": {
            "resident_levels_perc": (30.0, 50.0),
            "cpu_rescale_max": True,
        },
        "match": "~.*(fire)fox",
        "descr": "Resident percent memory levels total only - include_ram_map",
        "user": None,
    },
    {
        "default_params": {
            "cpulevels": (90.0, 98.0),
            "cpu_average": 15,
            "cpu_rescale_max": True,
        },
        "match": "~.*(fire)fox",
        "descr": "CPU levels average",
        "user": None,
    },
    {
        "default_params": {
            "virtual_levels": (90.0, 98.0),
            "virtual_average": 15,
        },
        "match": "~.*(fire)fox",
        "descr": "Virtual memory levels average",
        "user": None,
    },
    {
        "default_params": {
            "resident_levels": (90.0, 98.0),
            "resident_average": 15,
        },
        "match": "~.*(fire)fox",
        "descr": "Resident memory levels average",
        "user": None,
    },
    {
        "default_params": {
            "resident_levels_perc": (30.0, 40.0),
            "resident_perc_average": 15,
        },
        "match": "~.*(fire)fox",
        "descr": "Resident percent memory levels average - include_ram_map",
        "user": None,
    },
    {
        "default_params": {
            "resident_perc_average": 15,
        },
        "match": "~.*(fire)fox",
        "descr": "Resident percent memory levels average only - include_ram_map",
        "user": None,
    },
    {
        "default_params": {
            "resident_levels_perc": (90.0, 98.0),
            "resident_perc_average": 15,
        },
        "match": "~.*(fire)fox",
        "descr": "Resident percent memory levels no ram map",
        "user": None,
    },
    {
        "default_params": {
            "single_resident_levels": (10 * 1024**2, 15 * 1024**2),
        },
        "descr": "Resident memory levels single process",
        "match": "svchost.exe",
    },
    {
        "default_params": {
            "resident_levels": (30.0, 40.0),
            "resident_average": 0,
        },
        "descr": "Resident memory levels zero average",
        "match": "svchost.exe",
    },
    {},
]

PS_DISCOVERED_ITEMS = [
    Service(
        item="emacs on - include_ram_map",
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
    Service(
        item="CPU levels total only",
        parameters={
            "process": "~.*(fire)fox",
            "user": None,
            "cpulevels": (90.0, 98.0),
            "cpu_rescale_max": True,
            "match_groups": ("fire",),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="Virtual memory levels total only",
        parameters={
            "process": "~.*(fire)fox",
            "user": None,
            "virtual_levels": (90.0, 98.0),
            "cpu_rescale_max": True,
            "match_groups": ("fire",),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="Resident memory levels total only",
        parameters={
            "process": "~.*(fire)fox",
            "user": None,
            "resident_levels": (90.0, 98.0),
            "cpu_rescale_max": True,
            "match_groups": ("fire",),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="Resident percent memory levels total only - include_ram_map",
        parameters={
            "process": "~.*(fire)fox",
            "user": None,
            "resident_levels_perc": (30.0, 50.0),
            "cpu_rescale_max": True,
            "match_groups": ("fire",),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="CPU levels average",
        parameters={
            "process": "~.*(fire)fox",
            "user": None,
            "cpulevels": (90.0, 98.0),
            "cpu_average": 15,
            "cpu_rescale_max": True,
            "match_groups": ("fire",),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="Virtual memory levels average",
        parameters={
            "process": "~.*(fire)fox",
            "user": None,
            "virtual_levels": (90.0, 98.0),
            "virtual_average": 15,
            "match_groups": ("fire",),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="Resident memory levels average",
        parameters={
            "process": "~.*(fire)fox",
            "user": None,
            "resident_levels": (90.0, 98.0),
            "resident_average": 15,
            "match_groups": ("fire",),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="Resident percent memory levels average - include_ram_map",
        parameters={
            "process": "~.*(fire)fox",
            "user": None,
            "resident_levels_perc": (30.0, 40.0),
            "resident_perc_average": 15,
            "match_groups": ("fire",),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="Resident percent memory levels average only - include_ram_map",
        parameters={
            "process": "~.*(fire)fox",
            "user": None,
            "resident_perc_average": 15,
            "match_groups": ("fire",),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="Resident percent memory levels no ram map",
        parameters={
            "process": "~.*(fire)fox",
            "user": None,
            "resident_levels_perc": (90.0, 98.0),
            "resident_perc_average": 15,
            "match_groups": ("fire",),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="Resident memory levels single process",
        parameters={
            "process": "svchost.exe",
            "user": None,
            "single_resident_levels": (10 * 1024**2, 15 * 1024**2),
            "match_groups": (),
            "cgroup": (None, False),
        },
    ),
    Service(
        item="Resident memory levels zero average",
        parameters={
            "process": "svchost.exe",
            "user": None,
            "resident_levels": (30.0, 40.0),
            "resident_average": 0,
            "match_groups": (),
            "cgroup": (None, False),
        },
    ),
]


def test_inventory_common() -> None:
    info = list(itertools.chain.from_iterable(generate_inputs()))
    assert sorted(
        {
            s.item: s
            for s in ps_utils.discover_ps(
                PS_DISCOVERY_WATO_RULES,  # type: ignore[arg-type]
                ps_section._parse_ps(int(time.time()), info),
                None,
                None,
                None,
            )
        }.values(),
        key=lambda s: s.item or "",
    ) == sorted(PS_DISCOVERED_ITEMS, key=lambda s: s.item or "")


check_results = [
    [
        Result(
            state=State.OK,
            summary="Processes: 1",
        ),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Result(
            state=State.WARN,
            summary="Virtual memory: 1.00 GiB (warn/crit at 1.00 GiB/2.00 GiB)",
        ),
        Metric("vsz", 1050360, levels=(1073741824, 2147483648)),
        Result(
            state=State.OK,
            summary="Resident memory: 296 MiB",
        ),
        Metric("rss", 303252, levels=(1073741824, 2147483648)),
        Result(
            state=State.WARN,
            summary="Percentage of resident memory: 28.92% (warn/crit at 25.00%/50.00%)",
        ),
        Metric("pcpu", 0.0),
        Metric("pcpuavg", 0.0),
        Result(
            state=State.OK,
            summary="CPU: 0%, 15 min average: 0%",
        ),
        Result(
            state=State.OK,
            summary="Running for: 1 day 3 hours",
        ),
        Metric("age_youngest", 100779.0),
        Metric("age_oldest", 100779.0),
        Result(
            state=State.OK,
            notice=(
                "<table><tr><th>name</th><th>user</th><th>virtual size</th>"
                "<th>resident size</th><th>creation time</th><th>pid</th><th>cpu usage</th></tr>"
                "<tr><td>emacs</td><td>on</td><td>1.00 GiB</td><td>296 MiB</td>"
                "<td>2018-10-23 08:02:43</td><td>9902</td><td>0.0%</td></tr></table>"
            ),
        ),
    ],
    [
        Result(
            state=State.OK,
            summary="Processes: 1",
        ),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Result(
            state=State.OK,
            summary="Virtual memory: 2.79 GiB",
        ),
        Metric("vsz", 2924232),
        Result(
            state=State.OK,
            summary="Resident memory: 461 MiB",
        ),
        Metric("rss", 472252),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 7 hours 24 minutes"),
        Metric("age_youngest", 26655.0),
        Metric("age_oldest", 26655.0),
        Result(
            state=State.OK,
            notice=(
                "name /usr/lib/firefox/firefox, user on, virtual size 2.79 GiB,"
                " resident size 461 MiB, creation time 2018-10-24 04:38:07, pid 7912,"
                " cpu usage 0.0%\r\n"
            ),
        ),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=State.OK, summary="Virtual memory: 10.9 MiB"),
        Metric("vsz", 11180),
        Result(state=State.OK, summary="Resident memory: 1.12 MiB"),
        Metric("rss", 1144),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 3 hours 54 minutes"),
        Metric("age_youngest", 14050.0),
        Metric("age_oldest", 14050.0),
        Result(
            state=State.OK,
            notice=(
                "name /omd/sites/heute/lib/cmc/checkhelper, user heute, virtual size 10.9 MiB,"
                " resident size 1.12 MiB, creation time 2018-10-24 08:08:12, pid 10884,"
                " cpu usage 0.0%\r\n"
            ),
        ),
    ],
    [
        Result(state=State.OK, summary="Processes: 2"),
        Metric("count", 2, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=State.OK, summary="Virtual memory: 21.8 MiB"),
        Metric("vsz", 22360),
        Result(state=State.OK, summary="Resident memory: 2.33 MiB"),
        Metric("rss", 2388),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Youngest running for: 2 hours 37 minutes"),
        Metric("age_youngest", 9459.0),
        Result(state=State.OK, summary="Oldest running for: 3 hours 54 minutes"),
        Metric("age_oldest", 14050.0),
        Result(
            state=State.OK,
            notice=(
                "name /omd/sites/heute/lib/cmc/checkhelper, user heute, virtual size 10.9 MiB,"
                " resident size 1.12 MiB, creation time 2018-10-24 08:08:12, pid 10884,"
                " cpu usage 0.0%\r\nname /omd/sites/twelve/lib/cmc/checkhelper, user twelve,"
                " virtual size 10.9 MiB, resident size 1.21 MiB, creation time 2018-10-24 09:24:43, "
                "pid 30136, cpu usage 0.0%\r\n"
            ),
        ),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=State.OK, summary="Virtual memory: 10.9 MiB"),
        Metric("vsz", 11180),
        Result(state=State.OK, summary="Resident memory: 1.21 MiB"),
        Metric("rss", 1244),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 2 hours 37 minutes"),
        Metric("age_youngest", 9459.0),
        Metric("age_oldest", 9459.0),
        Result(
            state=State.OK,
            notice=(
                "name /omd/sites/twelve/lib/cmc/checkhelper, user twelve, virtual size 10.9 MiB,"
                " resident size 1.21 MiB, creation time 2018-10-24 09:24:43, pid 30136,"
                " cpu usage 0.0%\r\n"
            ),
        ),
    ],
    [
        Result(state=State.OK, summary="Processes: 2"),
        Metric("count", 2, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=State.OK, summary="Virtual memory: 20.7 MiB"),
        Metric("vsz", 21232),
        Result(state=State.OK, summary="Resident memory: 18.6 MiB"),
        Metric("rss", 19052),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 52 days 4 hours"),
        Metric("age_youngest", 4510565.0),
        Metric("age_oldest", 4510565.0),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 0 seconds"),
        Metric("age_youngest", 0.0),
        Metric("age_oldest", 0.0),
    ],
    [
        Result(state=State.OK, summary="Processes: 3"),
        Metric("count", 3, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=State.OK, summary="Virtual memory: 136 MiB"),
        Metric("vsz", 139532, levels=(1073741824000, 2147483648000)),
        Result(state=State.OK, summary="Resident memory: 38.6 MiB"),
        Metric("rss", 39516, levels=(104857600, 209715200)),
        Result(
            state=State.UNKNOWN,
            summary="Percentual RAM levels configured, but total RAM is unknown",
        ),
        Metric("pcpu", 0.0, levels=(90.0, 98.0)),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(
            state=State.WARN,
            summary="Process handles: 1204 (warn/crit at 1000/2000)",
        ),
        Metric("process_handles", 1204, levels=(1000, 2000)),
        Result(state=State.OK, summary="Youngest running for: 12 seconds"),
        Metric("age_youngest", 12.0),
        Result(
            state=State.WARN,
            summary=(
                "Oldest running for: 1 hour 11 minutes"
                " (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)"
            ),
        ),
        Metric("age_oldest", 4300.0, levels=(3600.0, 7200.0)),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=State.OK, summary="Virtual memory: 4.47 MiB"),
        Metric("vsz", 4576),
        Result(state=State.OK, summary="Resident memory: 316 KiB"),
        Metric("rss", 316),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Process handles: 53"),
        Metric("process_handles", 53),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1.0, levels=(100000, 100000), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Virtual memory: 2.79 GiB"),
        Metric("vsz", 2924232.0),
        Result(state=State.OK, summary="Resident memory: 461 MiB"),
        Metric("rss", 472252.0),
        Metric("pcpu", 0.0, levels=(90.0, 98.0)),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 7 hours 24 minutes"),
        Metric("age_youngest", 26655.0),
        Metric("age_oldest", 26655.0),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1.0, levels=(100000, 100000), boundaries=(0.0, None)),
        Result(state=State.CRIT, summary="Virtual memory: 2.79 GiB (warn/crit at 90 B/98 B)"),
        Metric("vsz", 2924232.0, levels=(90.0, 98.0)),
        Result(state=State.OK, summary="Resident memory: 461 MiB"),
        Metric("rss", 472252.0),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 7 hours 24 minutes"),
        Metric("age_youngest", 26655.0),
        Metric("age_oldest", 26655.0),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1.0, levels=(100000, 100000), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Virtual memory: 2.79 GiB"),
        Metric("vsz", 2924232.0),
        Result(state=State.CRIT, summary="Resident memory: 461 MiB (warn/crit at 90 B/98 B)"),
        Metric("rss", 472252.0, levels=(90.0, 98.0)),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 7 hours 24 minutes"),
        Metric("age_youngest", 26655.0),
        Metric("age_oldest", 26655.0),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1.0, levels=(100000, 100000), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Virtual memory: 2.79 GiB"),
        Metric("vsz", 2924232.0),
        Result(state=State.OK, summary="Resident memory: 461 MiB"),
        Metric("rss", 472252.0),
        Result(
            state=State.WARN,
            summary="Percentage of resident memory: 45.04% (warn/crit at 30.00%/50.00%)",
        ),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 7 hours 24 minutes"),
        Metric("age_youngest", 26655.0),
        Metric("age_oldest", 26655.0),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1.0, levels=(100000, 100000), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Virtual memory: 2.79 GiB"),
        Metric("vsz", 2924232.0),
        Result(state=State.OK, summary="Resident memory: 461 MiB"),
        Metric("rss", 472252.0),
        Metric("pcpu", 0.0, levels=(90.0, 98.0)),
        Metric("pcpuavg", 0.0, levels=(90.0, 98.0)),
        Result(state=State.OK, summary="CPU: 0%, 15 min average: 0%"),
        Result(state=State.OK, summary="Running for: 7 hours 24 minutes"),
        Metric("age_youngest", 26655.0),
        Metric("age_oldest", 26655.0),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1.0, levels=(100000, 100000), boundaries=(0.0, None)),
        Metric("vszavg", 2994413568.0, levels=(90.0, 98.0)),
        Result(
            state=State.CRIT,
            summary="Virtual memory: 2.79 GiB, 15 min average: 2.79 GiB (warn/crit at 90 B/98 B)",
        ),
        Metric("vsz", 2924232.0, levels=(90.0, 98.0)),
        Result(state=State.OK, summary="Resident memory: 461 MiB"),
        Metric("rss", 472252.0),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 7 hours 24 minutes"),
        Metric("age_youngest", 26655.0),
        Metric("age_oldest", 26655.0),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1.0, levels=(100000, 100000), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Virtual memory: 2.79 GiB"),
        Metric("vsz", 2924232.0),
        Metric("rssavg", 483586048.0, levels=(90.0, 98.0)),
        Result(
            state=State.CRIT,
            summary="Resident memory: 461 MiB, 15 min average: 461 MiB (warn/crit at 90 B/98 B)",
        ),
        Metric("rss", 472252.0, levels=(90.0, 98.0)),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 7 hours 24 minutes"),
        Metric("age_youngest", 26655.0),
        Metric("age_oldest", 26655.0),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1.0, levels=(100000, 100000), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Virtual memory: 2.79 GiB"),
        Metric("vsz", 2924232.0),
        Result(state=State.OK, summary="Resident memory: 461 MiB"),
        Metric("rss", 472252.0),
        Result(
            state=State.CRIT,
            summary=(
                "Percentage of resident memory: 45.04%, 15 min average: 45.04% (warn/crit at"
                " 30.00%/40.00%)"
            ),
        ),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 7 hours 24 minutes"),
        Metric("age_youngest", 26655.0),
        Metric("age_oldest", 26655.0),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1.0, levels=(100000, 100000), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Virtual memory: 2.79 GiB"),
        Metric("vsz", 2924232.0),
        Result(state=State.OK, summary="Resident memory: 461 MiB"),
        Metric("rss", 472252.0),
        Result(
            state=State.OK, summary="Percentage of resident memory: 45.04%, 15 min average: 45.04%"
        ),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 7 hours 24 minutes"),
        Metric("age_youngest", 26655.0),
        Metric("age_oldest", 26655.0),
    ],
    [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1.0, levels=(100000, 100000), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Virtual memory: 2.79 GiB"),
        Metric("vsz", 2924232.0),
        Result(state=State.OK, summary="Resident memory: 461 MiB"),
        Metric("rss", 472252.0),
        Result(
            state=State.UNKNOWN,
            summary="Percentual RAM levels configured, but total RAM is unknown",
        ),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 7 hours 24 minutes"),
        Metric("age_youngest", 26655.0),
        Metric("age_oldest", 26655.0),
    ],
    [
        Result(state=State.OK, summary="Processes: 3"),
        Metric("count", 3.0, levels=(100000, 100000), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Virtual memory: 136 MiB"),
        Metric("vsz", 139532.0),
        Result(state=State.OK, summary="Resident memory: 38.6 MiB"),
        Metric("rss", 39516.0),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(
            state=State.WARN,
            summary="svchost.exe with PID 600 resident memory: 10.4 MiB (warn/crit at 10.0 MiB/15.0 MiB)",
        ),
        Result(
            state=State.CRIT,
            summary="svchost.exe with PID 764 resident memory: 18.4 MiB (warn/crit at 10.0 MiB/15.0 MiB)",
        ),
        Result(state=State.OK, summary="Process handles: 1204"),
        Metric("process_handles", 1204.0),
        Result(state=State.OK, summary="Youngest running for: 12 seconds"),
        Metric("age_youngest", 12.0),
        Result(state=State.OK, summary="Oldest running for: 1 hour 11 minutes"),
        Metric("age_oldest", 4300.0),
    ],
    [
        Result(state=State.OK, summary="Processes: 3"),
        Metric("count", 3.0, levels=(100000, 100000), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Virtual memory: 136 MiB"),
        Metric("vsz", 139532.0),
        Result(
            state=State.CRIT,
            summary="Resident memory: 38.6 MiB (warn/crit at 30 B/40 B)",
        ),
        Metric("rss", 39516.0, levels=(30.0, 40.0)),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Process handles: 1204"),
        Metric("process_handles", 1204.0),
        Result(state=State.OK, summary="Youngest running for: 12 seconds"),
        Metric("age_youngest", 12.0),
        Result(state=State.OK, summary="Oldest running for: 1 hour 11 minutes"),
        Metric("age_oldest", 4300.0),
    ],
]


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "inv_item, reference",
    list(zip(PS_DISCOVERED_ITEMS, check_results)),
    ids=[s.item for s in PS_DISCOVERED_ITEMS],
)
def test_check_ps_common(inv_item: Service, reference: Sequence[Result | Metric]) -> None:
    parsed: list = []

    now = 1540375342
    for info in generate_inputs():
        _cpu_cores, data, _ = ps_section._parse_ps(now, info)
        parsed.extend((None, ps_info, cmd_line, now) for (ps_info, cmd_line) in data)

    factory_defaults = {**ps_check.CHECK_DEFAULT_PARAMETERS, **inv_item.parameters}
    item = inv_item.item
    assert item is not None
    with time_machine.travel(datetime.datetime(2024, 1, 1, tzinfo=ZoneInfo("CET"))):
        test_result = list(
            ps_utils.check_ps_common(
                label="Processes",
                item=item,
                params=factory_defaults,
                process_lines=parsed,
                cpu_cores=1,
                total_ram_map={"": 1024**3} if "include_ram_map" in item else {},
            )
        )
    assert test_result == reference


class cpu_config(NamedTuple):
    name: str
    agent_info: str
    cputime: float
    cpu_cores: int
    exp_load: float
    cpu_rescale_max: bool | None


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


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("data", cpu_util_data, ids=[a.name for a in cpu_util_data])
def test_check_ps_common_cpu(data: cpu_config) -> None:
    def time_info(service, agent_info, check_time, cputime, cpu_cores):
        _cpu_info, parsed_lines, ps_time = ps_section._parse_ps(
            check_time, splitter(agent_info.format(cputime))
        )
        lines_with_node_name = [
            (None, ps_info, cmd_line, ps_time) for (ps_info, cmd_line) in parsed_lines
        ]

        return list(
            ps_utils.check_ps_common(
                label="Processes",
                item=service.item,
                params=service.parameters,
                process_lines=lines_with_node_name,
                cpu_cores=cpu_cores,
                total_ram_map={},
            )
        )

    rescale_params = {
        "cpu_rescale_max": data.cpu_rescale_max if data.cpu_rescale_max is not None else False
    }
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
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=State.OK, summary="Virtual memory: 105 KiB"),
        Metric("vsz", 105),
        Result(state=State.OK, summary="Resident memory: 30.0 KiB"),
        Metric("rss", 30),
    ]
    assert output[8] == Result(state=State.OK, summary="Running for: 3 hours 59 minutes")


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "levels, reference",
    [
        (
            (1, 1, 99999, 99999),
            [
                Result(state=State.CRIT, summary="Processes: 0 (warn/crit below 1/1)"),
                Metric("count", 0, levels=(100000, 100000), boundaries=(0, None)),
            ],
        ),
        (
            (0, 0, 99999, 99999),
            [
                Result(state=State.OK, summary="Processes: 0"),
                Metric("count", 0, levels=(100000, 100000), boundaries=(0, None)),
            ],
        ),
    ],
)
def test_check_ps_common_count(
    levels: tuple[int, int, int, int], reference: Sequence[Result | Metric]
) -> None:
    _cpu_info, parsed_lines, ps_time = ps_section._parse_ps(
        int(time.time()), splitter("(on,105,30,00:00:{:02}/03:59:39,902) single")
    )
    lines_with_node_name = [
        (None, ps_info, cmd_line, ps_time) for (ps_info, cmd_line) in parsed_lines
    ]

    params = {
        "process": "~test",
        "user": None,
        "levels": levels,
    }

    output = list(
        ps_utils.check_ps_common(
            label="Processes",
            item="empty",
            params=params,
            process_lines=lines_with_node_name,
            cpu_cores=1,
            total_ram_map={},
        )
    )
    assert output == reference


@pytest.mark.usefixtures("initialised_item_state")
def test_subset_patterns() -> None:
    section_ps = ps_section._parse_ps(
        int(time.time()),
        splitter(
            """(user,0,0,0.5) main
(user,0,0,0.4) main_dev
(user,0,0,0.1) main_dev
(user,0,0,0.5) main_test"""
        ),
    )

    # Boundary in match is necessary otherwise main instance accumulates all
    inv_params: list[dict] = [
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

    test_discovered = ps_utils.discover_ps(inv_params, section_ps, None, None, None)
    assert {s.item: s for s in test_discovered} == {s.item: s for s in discovered}

    _, data, ps_time = section_ps
    for service, count in zip(discovered, [1, 2, 1]):
        assert isinstance(service.item, str)
        output = list(
            ps_utils.check_ps_common(
                label="Processes",
                item=service.item,
                params=service.parameters,
                process_lines=[(None, psi, cmd_line, ps_time) for (psi, cmd_line) in data],
                cpu_cores=1,
                total_ram_map={},
            )
        )
        assert output[0] == Result(state=State.OK, summary="Processes: %s" % count)


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("cpu_cores", [2, 4, 5])
def test_cpu_util_single_process_levels(cpu_cores: int) -> None:
    """Test CPU utilization per single process.
    - Check that Number of cores weight is active
    - Check that single process CPU utilization is present only on warn/crit states"""

    params: dict[str, Any] = {
        "process": "~.*firefox",
        "process_info": "text",
        "cpu_rescale_max": True,
        "levels": (1, 1, 99999, 99999),
        "single_cpulevels": (45.0, 80.0),
    }

    def run_check_ps_common_with_elapsed_time(check_time, cputime):
        agent_info = """(on,2275004,434008,00:00:49/26:58,25576) firefox
(on,1869920,359836,00:01:23/6:57,25664) firefox
(on,7962644,229660,00:00:10/26:56,25758) firefox
(on,1523536,83064,00:{:02}:00/26:55,25898) firefox"""
        _cpu_info, parsed_lines, ps_time = ps_section._parse_ps(
            check_time, splitter(agent_info.format(cputime))
        )
        lines_with_node_name = [
            (None, ps_info, cmd_line, ps_time) for (ps_info, cmd_line) in parsed_lines
        ]

        with time_machine.travel(datetime.datetime(2024, 1, 1, tzinfo=ZoneInfo("CET"))):
            return list(
                ps_utils.check_ps_common(
                    label="Processes",
                    item="firefox",
                    params=params,
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
    cpu_util_s = render.percent(cpu_util)
    single_msg = "firefox with PID 25898 CPU: %s (warn/crit at 45.00%%/80.00%%)" % cpu_util_s
    reference = [
        Result(state=State.OK, summary="Processes: 4"),
        Metric("count", 4, levels=(100000, 100000), boundaries=(0, None)),
        Result(state=State.OK, summary="Virtual memory: 13.0 GiB"),
        Metric("vsz", 13631104),
        Result(state=State.OK, summary="Resident memory: 1.06 GiB"),
        Metric("rss", 1106568),
        Metric("pcpu", cpu_util),
        Result(state=State.OK, summary="CPU: %s" % cpu_util_s),
        # beware! an item will be inserted here
        Result(state=State.OK, summary="Youngest running for: 6 minutes 57 seconds"),
        Metric("age_youngest", 417.0),
        Result(state=State.OK, summary="Oldest running for: 26 minutes 58 seconds"),
        Metric("age_oldest", 1618.0),
        Result(
            state=State.OK,
            notice="\r\n".join(
                [
                    "name firefox, user on, virtual size 2.17 GiB, resident size 424 MiB,"
                    " creation time 1970-01-01 00:34:02, pid 25576, cpu usage 0.0%",
                    "name firefox, user on, virtual size 1.78 GiB, resident size 351 MiB,"
                    " creation time 1970-01-01 00:54:03, pid 25664, cpu usage 0.0%",
                    "name firefox, user on, virtual size 7.59 GiB, resident size 224 MiB,"
                    " creation time 1970-01-01 00:34:04, pid 25758, cpu usage 0.0%",
                    "name firefox, user on, virtual size 1.45 GiB, resident size 81.1 MiB,"
                    " creation time 1970-01-01 00:34:05, pid 25898, cpu usage %.1f%%\r\n"
                    % cpu_util,
                ]
            ),
        ),
    ]
    if cpu_util >= params["single_cpulevels"][0]:
        reference.insert(
            8,
            Result(
                state=State.WARN if cpu_util < params["single_cpulevels"][1] else State.CRIT,
                summary=single_msg,
            ),
        )

    assert output == reference


@pytest.mark.usefixtures("initialised_item_state")
def test_parse_ps_windows(mocker: MockerFixture) -> None:
    section_ps = ps_section._parse_ps(
        int(time.time()),
        splitter(
            """(\\LS\0Checkmk,150364,40016,0,2080,1,387119531250,2225698437500,111,2,263652)	CPUSTRES64.EXE""",
            "\t",
        ),
    )

    section_mem = None
    section_mem_used = None
    section_cpu = None
    params = {**ps_check.CHECK_DEFAULT_PARAMETERS, "single_cpulevels": (0, 0, 0, 0)}

    service = next(
        iter(
            ps_utils.discover_ps(
                params=[
                    {"descr": "CPUSTRES64", "match": "CPUSTRES64.EXE", "default_params": {}},
                    {},
                ],
                section_ps=section_ps,
                section_mem=section_mem,
                section_mem_used=section_mem_used,
                section_cpu=section_cpu,
            )
        )
    )
    if service.item is None:
        assert False, "how do I not have an item"
    item = service.item

    mocker.patch("cmk.plugins.lib.ps.cpu_rate", return_value=1000000)
    mocker.patch("cmk.agent_based.v2.get_value_store", return_value={})
    results = list(
        ps_check.check_ps(
            item=item,
            params=params,
            section_ps=section_ps,
            section_mem=section_mem,
            section_mem_used=section_mem_used,
            section_cpu=section_cpu,
        )
    )
    single_process_result = next(
        r for r in results if isinstance(r, Result) and "PID 2080" in r.summary
    )
    assert single_process_result == Result(
        state=State.CRIT,
        summary="CPUSTRES64.EXE with PID 2080 CPU: 20.00% (warn/crit at 0%/0%)",
    )


# SUP-13009
_SECTION_EMPTY_CMD_LINE: ps_utils.Section = (
    1,
    [
        (
            ps_utils.PsInfo(
                user="root",
                virtual=96112,
                physical=3448,
                cputime="00:00:00/1-05:33:16",
                process_id="4515",
                pagefile=None,
                usermode_time=None,
                kernelmode_time=None,
                handles=None,
                threads=None,
                uptime=None,
                cgroup="12:pids:/system.slice/srcmstr.service,5:devices:/system.slice/srcmstr.service,1:name=systemd:/system.slice/srcmstr.service",
            ),
            [],
        ),
    ],
    int(time.time()),
)


def test_discover_empty_command_line() -> None:
    assert list(
        ps_utils.discover_ps(
            [
                {
                    "descr": "my_proc",
                    "match": "~^$",
                    "default_params": {"cpu_rescale_max": True},
                },
                {},
            ],
            _SECTION_EMPTY_CMD_LINE,
            None,
            None,
            None,
        )
    ) == [
        Service(
            item="my_proc",
            parameters={
                "process": "~^$",
                "match_groups": (),
                "user": None,
                "cgroup": (None, False),
                "cpu_rescale_max": True,
            },
        )
    ]


@pytest.mark.usefixtures("initialised_item_state")
def test_check_empty_command_line() -> None:
    assert list(
        ps_check.check_ps(
            "my_proc",
            {
                "process": "~^$",
                "match_groups": (),
                "user": None,
                "cgroup": (None, False),
                "cpu_rescale_max": True,
                "levels": (1, 1, 99999, 99999),
            },
            _SECTION_EMPTY_CMD_LINE,
            None,
            None,
            None,
        )
    ) == [
        Result(state=State.OK, summary="Processes: 1"),
        Metric("count", 1.0, levels=(100000.0, 100000.0), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Virtual memory: 93.9 MiB"),
        Metric("vsz", 96112.0),
        Result(state=State.OK, summary="Resident memory: 3.37 MiB"),
        Metric("rss", 3448.0),
        Metric("pcpu", 0.0),
        Result(state=State.OK, summary="CPU: 0%"),
        Result(state=State.OK, summary="Running for: 1 day 5 hours"),
        Metric("age_youngest", 106396.0),
        Metric("age_oldest", 106396.0),
    ]
