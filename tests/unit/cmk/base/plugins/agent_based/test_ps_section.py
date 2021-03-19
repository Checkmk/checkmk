#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# from collections import namedtuple
# import datetime
import itertools
from typing import List, Optional
#
import pytest  # type: ignore[import]
#
# from cmk.utils.type_defs import CheckPluginName
#
# from cmk.base.api.agent_based import value_store
# from cmk.base.discovered_labels import DiscoveredHostLabels, HostLabel
from cmk.base.plugins.agent_based import ps_section
from cmk.base.plugins.agent_based.utils import ps
#
# from checktestlib import CheckResult, assertCheckResultsEqual
#
# from testlib import on_time  # type: ignore[import]

pytestmark = pytest.mark.checks


def splitter(
    text: str,
    split_symbol: Optional[str] = None,
) -> List[List[str]]:
    return [line.split(split_symbol) for line in text.split("\n") if line]


def generate_inputs() -> List[List[List[str]]]:
    return [
        # CMK 1.5
        # linux, openwrt agent(5 entry, cmk>=1.2.7)
        # NOTE: It is important that the last line ("(twelve,...")
        #       remains the last line of the following output!
        splitter("""
(root,225948,9684,00:00:03/05:05:29,1) /sbin/init splash
(root,0,0,00:00:00/05:05:29,2) [kthreadd]
(on,288260,7240,00:00:00/05:03:00,4480) /usr/bin/gnome-keyring-daemon --start --foreground --components=secrets
(on,1039012,11656,00:00:00/05:02:41,5043) /usr/bin/pulseaudio --start --log-target=syslog
(on,1050360,303252,00:14:59/1-03:59:39,9902) emacs
(on,2924232,472252,00:12:05/07:24:15,7912) /usr/lib/firefox/firefox
(heute,11180,1144,00:00:00/03:54:10,10884) /omd/sites/heute/lib/cmc/checkhelper
(twelve,11180,1244,00:00:00/02:37:39,30136) /omd/sites/twelve/lib/cmc/checkhelper
"""),
        # solaris (5 entry cmk>=1.5)
        splitter("""
(root,4056,1512,0.0/52-04:56:05,5689) /usr/lib/ssh/sshd
(zombie,0,0,-/-,1952) <defunct>
(zombie,0,0,-/-,3952)
(zombie,0,0,-/-,4952)
"""),
        # windows agent
        splitter("""
(SYSTEM,0,0,0,0,0,0,0,0,1,0)	System Idle Process
(\\NT AUTHORITY\\SYSTEM,46640,10680,0,600,5212,27924179,58500375,370,11,12)	svchost.exe
(\\NT AUTHORITY\\NETWORK SERVICE,36792,10040,0,676,5588,492183155,189541215,380,8,50)	svchost.exe
(\\NT AUTHORITY\\LOCAL SERVICE,56100,18796,0,764,56632,1422261117,618855967,454,13,4300)	svchost.exe
(\\KLAPPRECHNER\\ab,29284,2948,0,3124,904,400576,901296,35,1,642)\tNOTEPAD.EXE
""", "\t"),
        # aix, bsd, hpux, macos, netbsd, openbsd agent(4 entry, cmk>=1.1.5)
        splitter("(db2prtl,17176,17540,0.0) /usr/lib/ssh/sshd"),
        # aix with zombies
        splitter("""
(oracle,9588,298788,0.0) ora_dmon_uc4prd
(<defunct>,,,)
(oracle,11448,300648,0.0) oraclemetroprd (LOCAL=NO)
"""),
        # windows agent(10 entry, cmk>1.2.5)
        splitter("""
(SYSTEM,0,0,0,0,0,0,0,0,2)	System Idle Process
(\\KLAPPRECHNER\\ab,29284,2948,0,3124,904,400576,901296,35,1)\tNOTEPAD.EXE
""", "\t"),
        # windows agent(wmic_info, cmk<1.2.5)# From server-windows-mssql-2
        splitter("""
[System Process]
System
System Idle Process
smss.exe
csrss.exe
csrss.exe
""", "\0") + splitter("""
[wmic process]
Node,HandleCount,KernelModeTime,Name,PageFileUsage,ProcessId,ThreadCount,UserModeTime,VirtualSize,WorkingSetSize
WSOPREKPFS01,0,388621186093750,System Idle Process,0,0,24,0,65536,24576
WSOPREKPFS01,1227,368895625000,System,132,4,273,0,14831616,10862592
WSOPREKPFS01,53,2031250,smss.exe,360,520,2,156250,4685824,323584
WSOPREKPFS01,679,10051718750,csrss.exe,2640,680,10,2222031250,70144000,2916352
WSOPREKPFS01,85,126562500,csrss.exe,1176,744,8,468750,44486656,569344
[wmic process end]
""", ","),
        # Second Generation
        splitter("""
(root) /usr/sbin/xinetd -pidfile /var/run/xinetd.pid -stayalive -inetd_compat -inetd_ipv6
"""),
        # First Generation
        splitter("""
/usr/sbin/xinetd -pidfile /var/run/xinetd.pid -stayalive -inetd_compat -inetd_ipv6
"""),
    ]


result_parse = [
    (1, [
        [("root", "225948", "9684", "00:00:03/05:05:29", "1"), "/sbin/init", "splash"],
        [("root", "0", "0", "00:00:00/05:05:29", "2"), "[kthreadd]"],
        [
            ("on", "288260", "7240", "00:00:00/05:03:00", "4480"),
            "/usr/bin/gnome-keyring-daemon", "--start", "--foreground", "--components=secrets"
        ],
        [
            ("on", "1039012", "11656", "00:00:00/05:02:41", "5043"), "/usr/bin/pulseaudio",
            "--start", "--log-target=syslog"
        ],
        [("on", "1050360", "303252", "00:14:59/1-03:59:39", "9902"),
         "emacs"],
        [("on", "2924232", "472252", "00:12:05/07:24:15", "7912"),
         "/usr/lib/firefox/firefox"],
        [("heute", "11180", "1144", "00:00:00/03:54:10", "10884"),
         "/omd/sites/heute/lib/cmc/checkhelper"],
        [("twelve", "11180", "1244", "00:00:00/02:37:39", "30136"),
         "/omd/sites/twelve/lib/cmc/checkhelper"],
    ]),
    (1, [
        [("root", "4056", "1512", "0.0/52-04:56:05", "5689"), "/usr/lib/ssh/sshd"],
        [("zombie", "0", "0", "-/-", "1952"), "<defunct>"],
    ]),
    (1, [
        [("SYSTEM", "0", "0", "0", "0", "0", "0", "0", "0", "1", "0"), "System Idle Process"],
        [
            ("\\NT AUTHORITY\\SYSTEM", "46640", "10680", "0", "600", "5212", "27924179", "58500375",
             "370", "11", "12"), "svchost.exe"
        ],
        [
            ("\\NT AUTHORITY\\NETWORK SERVICE", "36792", "10040", "0", "676", "5588", "492183155",
             "189541215", "380", "8", "50"), "svchost.exe"
        ],
        [
            ("\\NT AUTHORITY\\LOCAL SERVICE", "56100", "18796", "0", "764", "56632", "1422261117",
             "618855967", "454", "13", "4300"), "svchost.exe"
        ],
        [
            ("\\KLAPPRECHNER\\ab", "29284", "2948", "0", "3124", "904", "400576", "901296", "35",
             "1", "642"), "NOTEPAD.EXE"
        ],
    ]),
    (1, [[("db2prtl", "17176", "17540", "0.0"), "/usr/lib/ssh/sshd"]]),
    (1, [
        [("oracle", "9588", "298788", "0.0"), "ora_dmon_uc4prd"],
        [("oracle", "11448", "300648", "0.0"), "oraclemetroprd", "(LOCAL=NO)"],
    ]),
    (2, [
        [("SYSTEM", "0", "0", "0", "0", "0", "0", "0", "0", "2"), "System Idle Process"],
        [
            ("\\KLAPPRECHNER\\ab", "29284", "2948", "0", "3124", "904", "400576", "901296", "35",
             "1"), "NOTEPAD.EXE"
        ],
    ]),
    (24, [[(None,), u"[System Process]"],
          [
              ("unknown", "14484", "10608", "0", "4", "0", "0", "368895625000", "1227", "273", ""),
              u"System"
          ],
          [
              ("unknown", "64", "24", "0", "0", "0", "0", "388621186093750", "0", "24", ""),
              u"System Idle Process"
          ],
          [
              ("unknown", "4576", "316", "0", "520", "0", "156250", "2031250", "53", "2", ""),
              u"smss.exe"
          ],
          [
              ("unknown", "43444", "556", "0", "744", "1", "468750", "126562500", "85", "8", ""),
              u"csrss.exe"
          ],
          [
              ("unknown", "68500", "2848", "0", "680", "2", "2222031250", "10051718750", "679",
               "10", ""), u"csrss.exe"
          ]]),
    (1, [[
        ("root",), "/usr/sbin/xinetd", "-pidfile", "/var/run/xinetd.pid", "-stayalive",
        "-inetd_compat", "-inetd_ipv6"
    ]]),
    (1, [[
        (None,), "/usr/sbin/xinetd", "-pidfile", "/var/run/xinetd.pid", "-stayalive",
        "-inetd_compat", "-inetd_ipv6"
    ]]),
]


input_ids = [
    "linux, openwrt agent(5 entry, cmk>=1.2.7)",
    "solaris (5 entry cmk>=1.5)",
    "windows agent(11 entry, cmk>=)",
    "aix, bsd, hpux, macos, netbsd, openbsd, agent(4 entry, cmk>=1.1.5)",
    "aix with zombies",
    "windows agent(10 entry, cmk>1.2.5)",
    "windows agent(wmic_info, cmk<1.2.5)",
    "Second Generation user info only",
    "First Generation process only",
]


@pytest.mark.parametrize("capture, result", list(
    zip(generate_inputs(), result_parse),
), ids=input_ids)
def test_parse_ps(capture, result):
    cpu_core, lines = ps_section.parse_ps(capture)
    assert cpu_core == result[0]  # cpu_cores

    for (ps_info_item, cmd_line), ref in itertools.zip_longest(lines, result[1]):
        assert ps_info_item == ps.ps_info(*ref[0])
        assert cmd_line == ref[1:]
