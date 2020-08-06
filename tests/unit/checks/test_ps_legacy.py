#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
from collections import namedtuple
import datetime
import itertools
from typing import Any, Dict, List, Optional, Tuple

import pytest  # type: ignore[import]

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based import value_store
from cmk.base.discovered_labels import DiscoveredHostLabels, HostLabel
from cmk.base.plugins.agent_based import ps_section
from cmk.base.plugins.agent_based.utils import ps as ps_utils

from checktestlib import CheckResult, assertCheckResultsEqual

from testlib import on_time  # type: ignore[import]

pytestmark = pytest.mark.checks


@pytest.fixture(scope="module")
def ps_context(check_manager):
    check = check_manager.get_check("ps.perf")
    return check.context


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
        splitter("""(root,225948,9684,00:00:03/05:05:29,1) /sbin/init splash
(root,0,0,00:00:00/05:05:29,2) [kthreadd]
(on,288260,7240,00:00:00/05:03:00,4480) /usr/bin/gnome-keyring-daemon --start --foreground --components=secrets
(on,1039012,11656,00:00:00/05:02:41,5043) /usr/bin/pulseaudio --start --log-target=syslog
(on,1050360,303252,00:14:59/1-03:59:39,9902) emacs
(on,2924232,472252,00:12:05/07:24:15,7912) /usr/lib/firefox/firefox
(heute,11180,1144,00:00:00/03:54:10,10884) /omd/sites/heute/lib/cmc/checkhelper
(twelve,11180,1244,00:00:00/02:37:39,30136) /omd/sites/twelve/lib/cmc/checkhelper"""),
        # solaris (5 entry cmk>=1.5)
        splitter(
            """(root,4056,1512,0.0/52-04:56:05,5689) /usr/lib/ssh/sshd
(zombie,0,0,-/-,1952) <defunct>
(zombie,0,0,-/-,3952)
(zombie,0,0,-/-,4952) """),
        # windows agent
        splitter(
            """(SYSTEM,0,0,0,0,0,0,0,0,1,0)	System Idle Process
(\\NT AUTHORITY\\SYSTEM,46640,10680,0,600,5212,27924179,58500375,370,11,12)	svchost.exe
(\\NT AUTHORITY\\NETWORK SERVICE,36792,10040,0,676,5588,492183155,189541215,380,8,50)	svchost.exe
(\\NT AUTHORITY\\LOCAL SERVICE,56100,18796,0,764,56632,1422261117,618855967,454,13,4300)	svchost.exe
(\\KLAPPRECHNER\\ab,29284,2948,0,3124,904,400576,901296,35,1,642)\tNOTEPAD.EXE""", "\t"),
        # aix, bsd, hpux, macos, netbsd, openbsd agent(4 entry, cmk>=1.1.5)
        splitter("(db2prtl,17176,17540,0.0) /usr/lib/ssh/sshd"),
        # aix with zombies
        splitter("""(oracle,9588,298788,0.0) ora_dmon_uc4prd
(<defunct>,,,)
(oracle,11448,300648,0.0) oraclemetroprd (LOCAL=NO)"""),
        # windows agent(10 entry, cmk>1.2.5)
        splitter(
            """(SYSTEM,0,0,0,0,0,0,0,0,2)	System Idle Process
(\\KLAPPRECHNER\\ab,29284,2948,0,3124,904,400576,901296,35,1)\tNOTEPAD.EXE""", "\t"),
        # windows agent(wmic_info, cmk<1.2.5)# From server-windows-mssql-2
        splitter("""[System Process]
System
System Idle Process
smss.exe
csrss.exe
csrss.exe""", "\0") + splitter(
            """[wmic process]
Node,HandleCount,KernelModeTime,Name,PageFileUsage,ProcessId,ThreadCount,UserModeTime,VirtualSize,WorkingSetSize
WSOPREKPFS01,0,388621186093750,System Idle Process,0,0,24,0,65536,24576
WSOPREKPFS01,1227,368895625000,System,132,4,273,0,14831616,10862592
WSOPREKPFS01,53,2031250,smss.exe,360,520,2,156250,4685824,323584
WSOPREKPFS01,679,10051718750,csrss.exe,2640,680,10,2222031250,70144000,2916352
WSOPREKPFS01,85,126562500,csrss.exe,1176,744,8,468750,44486656,569344
[wmic process end]""", ","),
        # Second Generation
        splitter(
            "(root) /usr/sbin/xinetd -pidfile /var/run/xinetd.pid -stayalive -inetd_compat -inetd_ipv6"
        ),
        # First Generation
        splitter(
            "/usr/sbin/xinetd -pidfile /var/run/xinetd.pid -stayalive -inetd_compat -inetd_ipv6"),
    ]


PS_DISCOVERY_WATO_RULES = [  # type: ignore[var-annotated]
    {
        "default_params": {},
        "descr": "smss",
        "match": "~smss.exe"
    },
    {
        "default_params": {
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
        "match": "svchost.exe"
    },
    {
        "default_params": {
            "process_info": "text"
        },
        "match": "~.*(fire)fox",
        "descr": "firefox is on %s",
        "user": None,
    },
    {
        "default_params": {
            "process_info": "text"
        },
        "match": "~.*(fire)fox",
        "descr": "firefox is on %s",
        "user": None,
        "label": DiscoveredHostLabels(HostLabel(u'marco', u'polo'), HostLabel(u'peter', u'pan')),
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
        "user": False
    },
    {
        "default_params": {
            "max_age": (3600, 7200),
            "resident_levels_perc": (25.0, 50.0),
            "single_cpulevels": (90.0, 98.0),
            "resident_levels": (104857600, 209715200),
        },
        "match": "~.*cron",
        "descr": "cron",
        "user": "root"
    },
    {
        "default_params": {},
        "descr": "sshd",
        "match": "~.*sshd"
    },
    {
        'default_params': {},
        'descr': 'PS counter',
        'user': 'zombie',
    },
    {
        "default_params": {
            "process_info": "text"
        },
        "match": r"~/omd/sites/(\w+)/lib/cmc/checkhelper",
        "descr": "Checkhelpers %s",
        "user": None,
    },
    {
        "default_params": {
            "process_info": "text"
        },
        "match": r"~/omd/sites/\w+/lib/cmc/checkhelper",
        "descr": "Checkhelpers Overall",
        "user": None,
    },
]

PS_DISCOVERY_SPECS = [
    ("smss", "~smss.exe", None, (None, False), DiscoveredHostLabels(), {
        'cpu_rescale_max': None
    }),
    ("svchost", "svchost.exe", None, (None, False), {}, {
        "cpulevels": (90.0, 98.0),
        'cpu_rescale_max': None,
        "handle_count": (1000, 2000),
        "levels": (1, 1, 99999, 99999),
        "max_age": (3600, 7200),
        "resident_levels": (104857600, 209715200),
        "resident_levels_perc": (25.0, 50.0),
        "single_cpulevels": (90.0, 98.0),
        "virtual_levels": (1073741824000, 2147483648000),
    }),
    ("firefox is on %s", "~.*(fire)fox", None, (None, False), {}, {
        "process_info": "text",
        'cpu_rescale_max': None,
    }),
    ("firefox is on %s", "~.*(fire)fox", None, (None, False), DiscoveredHostLabels(HostLabel(u'marco', u'polo'), HostLabel(u'peter', u'pan')), {
        "process_info": "text",
        'cpu_rescale_max': None,
    }),
    ("emacs %u", "emacs", False, (None, False), {}, {
        "cpu_average": 15,
        'cpu_rescale_max': True,
        "process_info": "html",
        "resident_levels_perc": (25.0, 50.0),
        "virtual_levels": (1024**3, 2 * 1024**3),
        "resident_levels": (1024**3, 2 * 1024**3),
        "icon": "emacs.png",
    }),
    ("cron", "~.*cron", "root", (None, False), {}, {
        "max_age": (3600, 7200),
        'cpu_rescale_max': None,
        "resident_levels_perc": (25.0, 50.0),
        "single_cpulevels": (90.0, 98.0),
        "resident_levels": (104857600, 209715200)
    }),
    ("sshd", "~.*sshd", None, (None, False), {}, {
        'cpu_rescale_max': None
    }),
    ('PS counter', None, 'zombie', (None, False), {}, {
        'cpu_rescale_max': None
    }),
    ("Checkhelpers %s", r"~/omd/sites/(\w+)/lib/cmc/checkhelper", None, (None, False), {}, {
        "process_info": "text",
        'cpu_rescale_max': None,
    }),
    ("Checkhelpers Overall", r"~/omd/sites/\w+/lib/cmc/checkhelper", None, (None, False), {}, {
        "process_info": "text",
        'cpu_rescale_max': None,
    }),
]


def test_wato_rules():
    assert ps_utils.get_discovery_specs(PS_DISCOVERY_WATO_RULES) == PS_DISCOVERY_SPECS


@pytest.mark.parametrize("params, result", [
    (("sshd", 1, 1, 99, 99), {
        "process": "sshd",
        "user": None,
        "levels": (1, 1, 99, 99),
        'cpu_rescale_max': None,
    }),
    (("sshd", "root", 2, 2, 5, 5), {
        "process": "sshd",
        "user": "root",
        "levels": (2, 2, 5, 5),
        'cpu_rescale_max': None,
    }),
    ({
        "user": "foo",
        "process": "/usr/bin/foo",
        "warnmin": 1,
        "okmin": 1,
        "okmax": 3,
        "warnmax": 3,
    }, {
        "user": "foo",
        "process": "/usr/bin/foo",
        "levels": (1, 1, 3, 3),
        'cpu_rescale_max': None,
    }),
    ({
        "user": "foo",
        "process": "/usr/bin/foo",
        "levels": (1, 1, 3, 3),
        'cpu_rescale_max': True,
    }, {
        "user": "foo",
        "process": "/usr/bin/foo",
        "levels": (1, 1, 3, 3),
        'cpu_rescale_max': True,
    }),
])
def test_cleanup_params(ps_context, params, result):
    assert ps_context["ps_cleanup_params"](params) == result


PS_DISCOVERED_ITEMS = [
    ("emacs on", {
        "cpu_average": 15,
        'cpu_rescale_max': True,
        "resident_levels_perc": (25.0, 50.0),
        "process": "emacs",
        "icon": "emacs.png",
        "user": "on",
        "process_info": "html",
        "virtual_levels": (1024**3, 2 * 1024**3),
        "resident_levels": (1024**3, 2 * 1024**3),
        "match_groups": (),
        'cgroup': (None, False),
    }),
    ("firefox is on fire", {
        "process": "~.*(fire)fox",
        "process_info": "text",
        "user": None,
        'cpu_rescale_max': None,
        'match_groups': ('fire',),
        'cgroup': (None, False),
    }),
    ("Checkhelpers heute", {
        "process": "~/omd/sites/(\\w+)/lib/cmc/checkhelper",
        "process_info": "text",
        "user": None,
        'cpu_rescale_max': None,
        'match_groups': ('heute',),
        'cgroup': (None, False),
    }),
    ("Checkhelpers Overall", {
        "process": "~/omd/sites/\\w+/lib/cmc/checkhelper",
        "process_info": "text",
        "user": None,
        'match_groups': (),
        'cpu_rescale_max': None,
        'cgroup': (None, False),
    }),
    ("Checkhelpers twelve", {
        "process": "~/omd/sites/(\\w+)/lib/cmc/checkhelper",
        "process_info": "text",
        "user": None,
        'cpu_rescale_max': None,
        'match_groups': ('twelve',),
        'cgroup': (None, False),
    }),
    ("sshd", {
        "process": "~.*sshd",
        "user": None,
        'cpu_rescale_max': None,
        "match_groups": (),
        'cgroup': (None, False),
    }),
    ("PS counter", {
        'cpu_rescale_max': None,
        'process': None,
        'user': 'zombie',
        "match_groups": (),
        'cgroup': (None, False),
    }),
    ("svchost", {
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
        'cpu_rescale_max': None,
        "match_groups": (),
        'cgroup': (None, False),
    }),
    ("smss", {
        "process": "~smss.exe",
        "user": None,
        'cpu_rescale_max': None,
        "match_groups": (),
        'cgroup': (None, False),
    }),
]


def test_inventory_common(ps_context):
    info = list(itertools.chain.from_iterable(generate_inputs()))
    # nuke node info, b/c we never have node info during discovery
    _cpu_info, parsed_lines = ps_section.parse_ps(info)
    lines_with_node_name = [[None] + line for line in parsed_lines]

    assert ps_context["inventory_ps_common"](
        PS_DISCOVERY_WATO_RULES, lines_with_node_name) == PS_DISCOVERED_ITEMS


check_results = [
    CheckResult([
        (0, "Processes: 1", [("count", 1, 100000, 100000, 0)]),
        (1, "virtual: 1.00 GB (warn/crit at 1.00 GB/2.00 GB)", [("vsz", 1050360, 1073741824,
                                                                 2147483648, None, None)]),
        (0, "physical: 296.14 MB", [("rss", 303252, 1073741824, 2147483648, None, None)]),
        (1, "Percentage of total RAM: 28.92% (warn/crit at 25.0%/50.0%)"),
        (0, "CPU: 0%, 15 min average: 0%", [("pcpu", 0.0, None, None, None, None),
                                                ("pcpuavg", 0.0, None, None, 0, 15)]),
        (0, "running for: 27 h", []),
        (0,
         "\n<table><tr><th>name</th><th>user</th><th>virtual size</th><th>resident size</th><th>creation time</th><th>pid</th><th>cpu usage</th></tr><tr><td>emacs</td><td>on</td><td>1050360kB</td><td>303252kB</td><td>Oct 23 2018 08:02:43</td><td>9902</td><td>0.0%</td></tr></table>"
        ),
    ]),
    CheckResult([
        (0, "Processes: 1", [("count", 1, 100000, 100000, 0,
                           None)]),
        (0, "virtual: 2.79 GB", [("vsz", 2924232, None, None, None, None)]),
        (0, "physical: 461.18 MB", [("rss", 472252, None, None, None, None)]),
        (0, "CPU: 0%", [("pcpu", 0.0, None, None, None, None)]), (0, "running for: 7 h", []),
        (0,
         "\nname /usr/lib/firefox/firefox, user on, virtual size 2924232kB, resident size 472252kB, creation time Oct 24 2018 04:38:07, pid 7912, cpu usage 0.0%\r\n",
         [])
    ]),
    CheckResult([
        (0, "Processes: 1", [("count", 1, 100000, 100000, 0, None)]),
        (0, "virtual: 10.92 MB", [("vsz", 11180, None, None, None, None)]),
        (0, "physical: 1.12 MB", [("rss", 1144, None, None, None, None)]),
        (0, "CPU: 0%", [("pcpu", 0.0, None, None, None, None)]),
        (0, "running for: 234 m", []),
        (0, "\nname /omd/sites/heute/lib/cmc/checkhelper, user heute, virtual size 11180kB, resident size 1144kB, creation time Oct 24 2018 08:08:12, pid 10884, cpu usage 0.0%\r\n",
         [])
    ]),
    CheckResult([
        (0, "Processes: 2", [("count", 2, 100000, 100000, 0, None)]),
        (0, "virtual: 21.84 MB", [("vsz", 22360, None, None, None, None)]),
        (0, "physical: 2.33 MB", [("rss", 2388, None, None, None, None)]),
        (0, "CPU: 0%", [("pcpu", 0.0, None, None, None, None)]),
        (0, "youngest running for: 157 m", []),
        (0, "oldest running for: 234 m", []),
        (0, "\nname /omd/sites/heute/lib/cmc/checkhelper, user heute, virtual size 11180kB, resident size 1144kB, creation time Oct 24 2018 08:08:12, pid 10884, cpu usage 0.0%\r\nname /omd/sites/twelve/lib/cmc/checkhelper, user twelve, virtual size 11180kB, resident size 1244kB, creation time Oct 24 2018 09:24:43, pid 30136, cpu usage 0.0%\r\n",
         [])
    ]),
    CheckResult([
        (0, "Processes: 1", [("count", 1, 100000, 100000, 0, None)]),
        (0, "virtual: 10.92 MB", [("vsz", 11180, None, None, None, None)]),
        (0, "physical: 1.21 MB", [("rss", 1244, None, None, None, None)]),
        (0, "CPU: 0%", [("pcpu", 0.0, None, None, None, None)]),
        (0, "running for: 157 m", []),
        (0, "\nname /omd/sites/twelve/lib/cmc/checkhelper, user twelve, virtual size 11180kB, resident size 1244kB, creation time Oct 24 2018 09:24:43, pid 30136, cpu usage 0.0%\r\n",
         [])
    ]),
    CheckResult([
        (0, "Processes: 2", [("count", 2, 100000, 100000, 0, None)]),
        (0, "virtual: 20.73 MB", [("vsz", 21232, None, None, None, None)]),
        (0, "physical: 18.61 MB", [("rss", 19052, None, None, None, None)]),
        (0, "CPU: 0%", [("pcpu", 0.0, None, None, None, None)]),
        (0, "running for: 52 d", []),
    ]),
    CheckResult([(0, 'Processes: 1', [('count', 1, 100000, 100000, 0, None)]),
                 (0, 'CPU: 0%', [('pcpu', 0.0, None, None, None, None)]),
                 (0, 'running for: 0.00 s', [])]),
    CheckResult([
        (0, "Processes: 3", [("count", 3, 100000, 100000, 0, None)]),
        (0, "virtual: 136.26 MB", [("vsz", 139532, 1073741824000, 2147483648000, None, None)]),
        (0, "physical: 38.59 MB", [("rss", 39516, 104857600, 209715200, None, None)]),
        (3, "percentual RAM levels configured, but total RAM is unknown", []),
        (0, "CPU: 0%", [("pcpu", 0.0, 90.0, 98.0, None, None)]),
        (1, "process handles: 1204 (warn/crit at 1000/2000)", [("process_handles", 1204, 1000, 2000,
                                                                None, None)]),
        (0, "youngest running for: 12.0 s", []),
        (1, "oldest running for: 71 m (warn/crit at 60 m/120 m)", []),
    ]),
    CheckResult([
        (0, "Processes: 1", [("count", 1, 100000, 100000, 0, None)]),
        (0, "virtual: 4.47 MB", [("vsz", 4576, None, None, None, None)]),
        (0, "physical: 316.00 kB", [("rss", 316, None, None, None, None)]),
        (0, "CPU: 0%", [("pcpu", 0.0, None, None, None, None)]),
        (0, "process handles: 53", [("process_handles", 53, None, None, None, None)]),
    ]),
]


@pytest.mark.parametrize(
    "inv_item, reference",
    list(zip(PS_DISCOVERED_ITEMS, check_results)),
    ids=[a[0] for a in PS_DISCOVERED_ITEMS])
def test_check_ps_common(ps_context, inv_item, reference):
    parsed: List[List[Optional[str]]] = []
    for info in generate_inputs():
        _cpu_cores, data = ps_section.parse_ps(info)
        parsed.extend([None] + line for line in data)
    total_ram = 1024**3 if "emacs" in inv_item[0] else None
    with on_time(1540375342, "CET"):
        factory_defaults = {"levels": (1, 1, 99999, 99999)}
        factory_defaults.update(inv_item[1])
        with value_store.context(CheckPluginName("ps"), "unit-test"):
            test_result = CheckResult(ps_context["check_ps_common"](
                inv_item[0], factory_defaults, parsed, total_ram=total_ram))
        assertCheckResultsEqual(test_result, reference)


cpu_config = namedtuple("CPU_config", "name agent_info cputime cpu_cores exp_load cpu_rescale_max")
cpu_util_data = [
    cpu_config('linux no cpu scale conf 1 core', "(on,105,30,00:00:{:02}/03:59:39,902) test", 30, 1,
               50, None),
    cpu_config('linux no cpu scale conf 2 cores', "(on,105,30,00:00:{:02}/03:59:39,902) test", 30,
               2, 50, None),
    cpu_config('linux No_Core_division 2 cores', "(on,105,30,00:00:{:02}/03:59:39,902) test", 120,
               2, 200, False),
    cpu_config('linux Core_division 2 cores', "(on,105,30,00:00:{:02}/03:59:39,902) test", 30, 2,
               25, True),
    cpu_config("Win no cpu scale conf 2 cores",
               "(\\KLAPPRECHNER\ab,105,30,0,3124,904,{0}0000000,{0}0000000,0,1,14340) test.exe", 54,
               2, 90, None),
    cpu_config("Win No_Core_division 2 cores",
               "(\\KLAPPRECHNER\ab,105,30,0,3124,904,{0}0000000,{0}0000000,0,1,14340) test.exe", 54,
               2, 180, False),
    cpu_config("Win Core_division 2 cores",
               "(\\KLAPPRECHNER\ab,105,30,0,3124,904,{0}0000000,{0}0000000,0,1,14340) test.exe", 54,
               2, 90, True),
    cpu_config('Solaris,BSD,etc no cpu conf 1 core', "(on,105,30,{}/03:59:39,902) test", 30.8, 1,
               30.8, None),
    cpu_config('Solaris,BSD,etc no cpu conf 2 cores', "(on,105,30,{}/03:59:39,902) test", 174.8, 2,
               174.8, None),
    cpu_config('Solaris,BSD,etc No_Core_division 2 cores', "(on,105,30,{}/03:59:39,902) test",
               174.8, 2, 174.8, False),
    cpu_config('Solaris,BSD,etc Core_division 2 cores', "(on,105,30,{}/03:59:39,902) test", 174.8,
               2, 174.8 / 2, True),
]


@pytest.mark.parametrize("data", cpu_util_data, ids=[a.name for a in cpu_util_data])
def test_check_ps_common_cpu(ps_context, monkeypatch, data):
    def time_info(agent_info, check_time, cputime, cpu_cores):
        with on_time(datetime.datetime.utcfromtimestamp(check_time), "CET"):
            _cpu_info, parsed_lines = ps_section.parse_ps(splitter(agent_info.format(cputime)))
            lines_with_node_name = [[None] + line for line in parsed_lines]

            return CheckResult(ps_context["check_ps_common"](
                inv_item[0], inv_item[1], lines_with_node_name, cpu_cores=cpu_cores))

    inv_item = (
        "test",
        {
            "process": "~test",
            "user": None,
            "levels": (1, 1, 99999, 99999)  # from factory defaults
        })
    if data.cpu_rescale_max is not None:
        inv_item[1].update({"cpu_rescale_max": data.cpu_rescale_max})

    with value_store.context(CheckPluginName("ps"), "unit-test"):
        # Initialize counters
        time_info(data.agent_info, 0, 0, data.cpu_cores)
        # Check_cpu_utilization
        output = time_info(data.agent_info, 60, data.cputime, data.cpu_cores)

    reference = CheckResult([
        (0, "Processes: 1", [("count", 1, 100000, 100000, 0)]),
        (0, "virtual: 105.00 kB", [("vsz", 105, None, None, None, None)]),
        (0, "physical: 30.00 kB", [("rss", 30, None, None, None, None)]),
        ps_context["cpu_check"](data.exp_load, inv_item[0], inv_item[1]),
        (0, "running for: 239 m", []),
    ])

    assertCheckResultsEqual(output, reference)


@pytest.mark.parametrize("levels, reference", [
    ((1, 1, 99999, 99999),
     CheckResult([
         (2, "Processes: 0 (warn/crit below 1/1)", [("count", 0, 100000, 100000, 0)]),
     ])),
    ((0, 0, 99999, 99999), CheckResult([
        (0, "Processes: 0", [("count", 0, 100000, 100000, 0)]),
    ])),
])
def test_check_ps_common_count(ps_context, levels, reference):
    _cpu_info, parsed_lines = ps_section.parse_ps(
        splitter("(on,105,30,00:00:{:02}/03:59:39,902) single"))
    lines_with_node_name = [[None] + line for line in parsed_lines]

    params = {
        "process": "~test",
        "user": None,
        "levels": levels,
    }

    output = CheckResult(ps_context["check_ps_common"](
        'empty', params, lines_with_node_name, cpu_cores=1))
    assertCheckResultsEqual(output, reference)


def test_subset_patterns(check_manager):

    check = check_manager.get_check("ps.perf")
    check.set_check_api_utils_globals()  # needed for host name

    _cpu_info, parsed_lines = ps_section.parse_ps(
        splitter("""(user,0,0,0.5) main
(user,0,0,0.4) main_dev
(user,0,0,0.1) main_dev
(user,0,0,0.5) main_test"""))

    lines_with_node_name = [[None] + line for line in parsed_lines]

    # Boundary in match is necessary otherwise main instance accumulates all
    inv_params: List[Dict] = [{
        'default_params': {
            'cpu_rescale_max': True,
            'levels': (1, 1, 99999, 99999)
        },
        'match': '~(main.*)\\b',
        'descr': '%s',
    }]

    discovered = [
        ('main', {
            'cpu_rescale_max': True,
            'levels': (1, 1, 99999, 99999),
            'process': '~(main.*)\\b',
            'match_groups': ('main',),
            'user': None,
            'cgroup': (None, False),
        }),
        ('main_dev', {
            'cpu_rescale_max': True,
            'levels': (1, 1, 99999, 99999),
            'process': '~(main.*)\\b',
            'match_groups': ('main_dev',),
            'user': None,
            'cgroup': (None, False),
        }),
        ('main_test', {
            'cpu_rescale_max': True,
            'levels': (1, 1, 99999, 99999),
            'process': '~(main.*)\\b',
            'match_groups': ('main_test',),
            'user': None,
            'cgroup': (None, False),
        }),
    ]

    assert check.context["inventory_ps_common"](inv_params, lines_with_node_name) == discovered

    def counted_reference(count):
        return CheckResult([
            (0, "Processes: %s" % count, [("count", count, 100000, 100000, 0, None)]),
            (0, "CPU: 0.5%", [("pcpu", 0.5, None, None, None, None)]),
        ])

    for (item, params), count in zip(discovered, [1, 2, 1]):
        output = CheckResult(check.context["check_ps_common"](item, params, lines_with_node_name, cpu_cores=1))
        assertCheckResultsEqual(output, counted_reference(count))


@pytest.mark.parametrize("cpu_cores", [2, 4, 5])
def test_cpu_util_single_process_levels(ps_context, cpu_cores):
    """Test CPU utilization per single process.
- Check that Number of cores weight is active
- Check that single process CPU utilization is present only on warn/crit states"""

    params: Dict[str, Any] = {
        'process': '~.*firefox',
        'process_info': "text",
        'cpu_rescale_max': True,
        'levels': (1, 1, 99999, 99999),
        'single_cpulevels': (45.0, 80.0),
    }

    def run_check_ps_common_with_elapsed_time(check_time, cputime):
        with on_time(check_time, "CET"):
            agent_info = """(on,2275004,434008,00:00:49/26:58,25576) firefox
(on,1869920,359836,00:01:23/6:57,25664) firefox
(on,7962644,229660,00:00:10/26:56,25758) firefox
(on,1523536,83064,00:{:02}:00/26:55,25898) firefox"""
            _cpu_info, parsed_lines = ps_section.parse_ps(splitter(agent_info.format(cputime)))
            lines_with_node_name = [[None] + line for line in parsed_lines]

            return CheckResult(ps_context["check_ps_common"](
            'firefox', params, lines_with_node_name, cpu_cores=cpu_cores))

    with value_store.context(CheckPluginName("ps"), "unit-test"):
        # CPU utilization is a counter, initialize it
        run_check_ps_common_with_elapsed_time(0, 0)
        # CPU utilization is a counter, after 60s time, one process consumes 2 min of CPU
        output = run_check_ps_common_with_elapsed_time(60, 2)

    cpu_util = 200.0 / cpu_cores
    cpu_util_s = ps_context['get_percent_human_readable'](cpu_util)
    single_msg = 'firefox with PID 25898 CPU: %s (warn/crit at 45.0%%/80.0%%)' % cpu_util_s
    reference = [
        (0, "Processes: 4", [("count", 4, 100000, 100000, 0)]),
        (0, "virtual: 13.00 GB", [("vsz", 13631104, None, None, None, None)]),
        (0, "physical: 1.06 GB", [("rss", 1106568, None, None, None, None)]),
        (0, "CPU: %s" % cpu_util_s, [('pcpu', cpu_util, None, None, None, None)]),
        (0, 'youngest running for: 6 m', []),
        (0, 'oldest running for: 26 m', []),
        (0, "\r\n".join([
            '\nname firefox, user on, virtual size 2275004kB, resident size 434008kB, creation time Jan 01 1970 00:34:02, pid 25576, cpu usage 0.0%',
            'name firefox, user on, virtual size 1869920kB, resident size 359836kB, creation time Jan 01 1970 00:54:03, pid 25664, cpu usage 0.0%',
            'name firefox, user on, virtual size 7962644kB, resident size 229660kB, creation time Jan 01 1970 00:34:04, pid 25758, cpu usage 0.0%',
            'name firefox, user on, virtual size 1523536kB, resident size 83064kB, creation time Jan 01 1970 00:34:05, pid 25898, cpu usage %.1f%%\r\n'
            % cpu_util,
        ]))
    ]

    if cpu_util > params['single_cpulevels'][1]:
        reference.insert(4, (2, single_msg, []))
    elif cpu_util > params['single_cpulevels'][0]:
        reference.insert(4, (1, single_msg, []))

    assertCheckResultsEqual(output, CheckResult(reference))
