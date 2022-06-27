#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import typing as t

import pytest

from tests.testlib import Check

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.checks


class TupleTestData(t.NamedTuple):
    input: t.List[str]
    output: t.Dict[str, t.Dict[str, t.Union[None, str, int, t.List[str]]]]


TEST_DATA = [
    # Output from multipath -l has the following possible formats (see input):
    TupleTestData(
        input=[
            "orabase.lun50 (360a9800043346937686f456f59386741) dm-15 NETAPP,LUN",
            "[size=25G][features=1 queue_if_no_path][hwhandler=0]",
            r"\_ round-robin 0 [prio=0][active]",
            r" \_ 1:0:3:50 sdy 65:128 [active][undef]",
            r" \_ 3:0:3:50 sdz 65:144 [active][undef]",
        ],
        output={
            "360a9800043346937686f456f59386741": {
                "paths": ["sdy", "sdz"],
                "broken_paths": [],
                "luns": ["1:0:3:50(sdy)", "3:0:3:50(sdz)"],
                "uuid": "360a9800043346937686f456f59386741",
                "state": "[prio=0][active]",
                "numpaths": 2,
                "device": "dm-15",
                "alias": "orabase.lun50",
            },
        },
    ),
    TupleTestData(
        # An alias might not be defined. The out is then:
        input=[
            "360a980004334644d654a364469555a76",
            '[size=300 GB][features="0"][hwhandler="0"]',
            r"\_ round-robin 0 [active]",
            r" \_ 1:0:2:13 sdc 8:32  [active][ready]",
            r" \_ 3:0:2:13 sdl 8:176 [active][ready]",
        ],
        output={
            "360a980004334644d654a364469555a76": {
                "paths": ["sdc", "sdl"],
                "broken_paths": [],
                "luns": ["1:0:2:13(sdc)", "3:0:2:13(sdl)"],
                "uuid": "360a980004334644d654a364469555a76",
                "state": None,
                "numpaths": 2,
                "device": None,
            },
        },
    ),
    TupleTestData(
        # Might also be local disks:
        input=[
            "SFUJITSU_MAW3073NC_DBL2P62003VT",
            '[size=68 GB][features="0"][hwhandler="0"]',
            r"\_ round-robin 0 [active]",
            r" \_ 0:0:3:0  sdb 8:16  [active][ready]",
        ],
        output={
            "SFUJITSU_MAW3073NC_DBL2P62003VT": {
                "paths": ["sdb"],
                "broken_paths": [],
                "luns": ["0:0:3:0(sdb)"],
                "uuid": "SFUJITSU_MAW3073NC_DBL2P62003VT",
                "state": None,
                "numpaths": 1,
                "device": None,
            }
        },
    ),
    TupleTestData(
        # Some very special header line
        # (No space between uuid and dm-* - strange...)
        input=[
            "360a980004334644d654a316e65306e51dm-4 NETAPP,LUN",
            "[size=30G][features=1 queue_if_no_path][hwhandler=0]",
            r"\_ round-robin 0 [prio=0][active]",
            r" \_ 1:0:2:50 sdg 8:96  [active][undef]",
            r"\_ round-robin 0 [prio=0][enabled]",
            r" \_ 4:0:1:50 sdl 8:176 [active][undef]",
        ],
        output={
            "360a980004334644d654a316e65306e51": {
                "paths": ["sdg", "sdl"],
                "broken_paths": [],
                "luns": ["1:0:2:50(sdg)", "4:0:1:50(sdl)"],
                "uuid": "360a980004334644d654a316e65306e51",
                "state": "[prio=0][enabled]",
                "numpaths": 2,
                "device": "dm-4",
            }
        },
    ),
    TupleTestData(
        # And another one:
        input=[
            "1494554000000000052303250303700000000000000000000 dm-0 IET,VIRTUAL-DISK",
            "[size=70G][features=0][hwhandler=0][rw]",
            r"\_ round-robin 0 [prio=-1][active]",
            r" \_ 3:0:0:0 sdb 8:16  [active][undef]",
            r"\_ round-robin 0 [prio=-1][enabled]",
            r" \_ 4:0:0:0 sdc 8:32  [active][undef]",
        ],
        output={
            "1494554000000000052303250303700000000000000000000": {
                "paths": ["sdb", "sdc"],
                "broken_paths": [],
                "luns": ["3:0:0:0(sdb)", "4:0:0:0(sdc)"],
                "uuid": "1494554000000000052303250303700000000000000000000",
                "state": "[prio=-1][enabled]",
                "numpaths": 2,
                "device": "dm-0",
            }
        },
    ),
    TupleTestData(
        # Other output from other host:
        input=[
            "anzvol2 (36005076306ffc648000000000000510a) dm-15 IBM,2107900",
            "[size=100G][features=0][hwhandler=0]",
            r"\_ round-robin 0 [prio=-6][active]",
            r" \_ 4:0:5:1  sdbf 67:144 [active][undef]",
            r" \_ 4:0:4:1  sdau 66:224 [active][undef]",
            r" \_ 4:0:3:1  sdaj 66:48  [active][undef]",
            r" \_ 3:0:5:1  sdy  65:128 [active][undef]",
            r" \_ 3:0:4:1  sdn  8:208  [active][undef]",
            r" \_ 3:0:3:1  sdc  8:32   [active][undef]",
            "anzvol1 (36005076306ffc6480000000000005005) dm-16 IBM,2107900",
            "[size=165G][features=0][hwhandler=0]",
            r"\_ round-robin 0 [prio=-6][active]",
            r" \_ 4:0:5:0  sdbe 67:128 [active][undef]",
            r" \_ 4:0:4:0  sdat 66:208 [active][undef]",
            r" \_ 4:0:3:0  sdai 66:32  [active][undef]",
            r" \_ 3:0:5:0  sdx  65:112 [active][undef]",
            r" \_ 3:0:4:0  sdm  8:192  [active][undef]",
            r" \_ 3:0:3:0  sdb  8:16   [active][undef]",
        ],
        output={
            "36005076306ffc6480000000000005005": {
                "paths": ["sdbe", "sdat", "sdai", "sdx", "sdm", "sdb"],
                "broken_paths": [],
                "luns": [
                    "4:0:5:0(sdbe)",
                    "4:0:4:0(sdat)",
                    "4:0:3:0(sdai)",
                    "3:0:5:0(sdx)",
                    "3:0:4:0(sdm)",
                    "3:0:3:0(sdb)",
                ],
                "uuid": "36005076306ffc6480000000000005005",
                "state": "[prio=-6][active]",
                "numpaths": 6,
                "device": "dm-16",
                "alias": "anzvol1",
            },
            "36005076306ffc648000000000000510a": {
                "paths": ["sdbf", "sdau", "sdaj", "sdy", "sdn", "sdc"],
                "broken_paths": [],
                "luns": [
                    "4:0:5:1(sdbf)",
                    "4:0:4:1(sdau)",
                    "4:0:3:1(sdaj)",
                    "3:0:5:1(sdy)",
                    "3:0:4:1(sdn)",
                    "3:0:3:1(sdc)",
                ],
                "uuid": "36005076306ffc648000000000000510a",
                "state": "[prio=-6][active]",
                "numpaths": 6,
                "device": "dm-15",
                "alias": "anzvol2",
            },
        },
    ),
    TupleTestData(
        # And one other output (ID has not 33 times A-Z0-9):
        input=[
            "mpath1 (SIBM_____SwapA__________DA02BF71)",
            '[size=41 GB][features="0"][hwhandler="0"]',
            r"\_ round-robin 0 [active]",
            r" \_ 1:0:1:0 sdd 8:48  [active]",
        ],
        output={
            "SIBM_____SwapA__________DA02BF71": {
                "paths": ["sdd"],
                "broken_paths": [],
                "luns": ["1:0:1:0(sdd)"],
                "uuid": "SIBM_____SwapA__________DA02BF71",
                "state": None,
                "numpaths": 1,
                "device": None,
                "alias": "mpath1",
            }
        },
    ),
    TupleTestData(
        # Recently I've seen this output >:-P
        input=[
            "360080e500017bd72000002eb4c1b1ae8 dm-1 IBM,1814      FAStT",
            "size=350G features='1 queue_if_no_path' hwhandler='1 rdac' wp=rw",
            "`-+- policy='round-robin 0' prio=-1 status=active",
            "  |- 7:0:2:81 sdd 8:48   active undef running",
            "  `- 8:0:2:81 sdp 8:240  active undef running",
        ],
        output={
            "360080e500017bd72000002eb4c1b1ae8": {
                "paths": ["sdd", "sdp"],
                "broken_paths": [],
                "luns": ["7:0:2:81(sdd)", "8:0:2:81(sdp)"],
                "uuid": "360080e500017bd72000002eb4c1b1ae8",
                "state": "prio=-1status=active",
                "numpaths": 2,
                "device": "dm-1",
            }
        },
    ),
    # And this has been seen on SLES 11 SP1 64 Bit:
    TupleTestData(
        input=[
            "3600508b40006d7da0001a00004740000 dm-0 HP,HSV210",
            "size=10G features='1 queue_if_no_path' hwhandler='0' wp=rw",
            "|-+- policy='round-robin 0' prio=-1 status=active",
            "| |- 2:0:0:1 sda        8:0    active undef running",
            "| `- 3:0:0:1 sdo        8:224  active undef running",
            "`-+- policy='round-robin 0' prio=-1 status=enabled",
            "  |- 3:0:1:1 sdv        65:80  active undef running",
            "  `- 2:0:1:1 sdh        8:112  active undef running",
        ],
        output={
            "3600508b40006d7da0001a00004740000": {
                "paths": ["sda", "sdo", "sdv", "sdh"],
                "broken_paths": [],
                "luns": ["2:0:0:1(sda)", "3:0:0:1(sdo)", "3:0:1:1(sdv)", "2:0:1:1(sdh)"],
                "uuid": "3600508b40006d7da0001a00004740000",
                "state": "prio=-1status=enabled",
                "numpaths": 4,
                "device": "dm-0",
            }
        },
    ),
    # This is another output, which made problems up to
    # 1.1.12:
    TupleTestData(
        input=[
            "SDDN_S2A_9900_1308xxxxxxxx dm-13 DDN,S2A 9900",
            "[size=7.3T][features=0][hwhandler=0][rw]",
            r"\_ round-robin 0 [prio=0][active]",
            r" \_ 3:0:1:11 sdaj 66:48   [failed][undef]",
            r" \_ 4:0:0:11 sdbh 67:176  [failed][undef]",
            r" \_ 4:0:2:11 sddd 70:176  [active][undef]",
            r" \_ 3:0:2:11 sdeb 128:48  [active][undef]",
            r"\_ round-robin 0 [prio=0][enabled]",
            r" \_ 4:0:1:11 sdcf 69:48   [active][undef]",
            r" \_ 3:0:0:11 sdl  8:176   [active][undef]",
        ],
        output={
            "SDDN_S2A_9900_1308xxxxxxxx": {
                "paths": ["sdaj", "sdbh", "sddd", "sdeb", "sdcf", "sdl"],
                "broken_paths": ["3:0:1:11(sdaj)", "4:0:0:11(sdbh)"],
                "luns": [
                    "3:0:1:11(sdaj)",
                    "4:0:0:11(sdbh)",
                    "4:0:2:11(sddd)",
                    "3:0:2:11(sdeb)",
                    "4:0:1:11(sdcf)",
                    "3:0:0:11(sdl)",
                ],
                "uuid": "SDDN_S2A_9900_1308xxxxxxxx",
                "state": "[prio=0][enabled]",
                "numpaths": 6,
                "device": "dm-13",
            }
        },
    ),
    TupleTestData(
        # Just an underscore and a dash in the LUN name
        input=[
            "SDataCoreSANsymphony_DAT05-fscl dm-6 DataCore,SANsymphony",
            "[size=600G][features=0][hwhandler=0]",
            r"\_ round-robin 0 [prio=-1][enabled]",
            r" \_ 3:0:0:11 sdae 65:224 [active][undef]",
            r"\_ round-robin 0 [prio=-1][enabled]",
            r" \_ 4:0:0:11 sdt  65:48  [active][undef]",
        ],
        output={
            "SDataCoreSANsymphony_DAT05-fscl": {
                "paths": ["sdae", "sdt"],
                "broken_paths": [],
                "luns": ["3:0:0:11(sdae)", "4:0:0:11(sdt)"],
                "uuid": "SDataCoreSANsymphony_DAT05-fscl",
                "state": "[prio=-1][enabled]",
                "numpaths": 2,
                "device": "dm-6",
            }
        },
    ),
    TupleTestData(
        # This one here is from RedHat 6. Very creative...
        input=[
            "1IET     00010001 dm-4 IET,VIRTUAL-DISK",
            "size=200G features='0' hwhandler='0' wp=rw",
            "|-+- policy='round-robin 0' prio=0 status=active",
            "| `- 23:0:0:1   sdk  8:160   active undef running",
            "|-+- policy='round-robin 0' prio=0 status=enabled",
            "| `- 21:0:0:1   sdj  8:144   active undef running",
            "|-+- policy='round-robin 0' prio=0 status=enabled",
            "| `- 22:0:0:1   sdg  8:96    active undef running",
            "`-+- policy='round-robin 0' prio=0 status=enabled",
            "  `- 20:0:0:1   sdi  8:128   active undef running",
        ],
        output={
            "1IET 00010001": {
                "paths": ["sdk", "sdj", "sdg", "sdi"],
                "broken_paths": [],
                "luns": ["23:0:0:1(sdk)", "21:0:0:1(sdj)", "22:0:0:1(sdg)", "20:0:0:1(sdi)"],
                "uuid": "1IET 00010001",
                "state": "prio=0status=enabled",
                "numpaths": 4,
                "device": "dm-4",
            }
        },
    ),
    TupleTestData(
        # And a completely new situation:
        input=[
            "Nov 05 17:17:03 | DM multipath kernel driver not loaded",
            "Nov 05 17:17:03 | /etc/multipath.conf does not exist, blacklisting all devices.",
            "Nov 05 17:17:03 | A sample multipath.conf file is located at",
            "Nov 05 17:17:03 | /usr/share/doc/device-mapper-multipath-0.4.9/multipath.conf",
            "Nov 05 17:17:03 | You can run /sbin/mpathconf to create or modify /etc/multipath.conf",
            "Nov 05 17:17:03 | DM multipath kernel driver not loaded",
        ],
        output={},
    ),
    TupleTestData(
        # UUID which includes dots (seen on Oracle Exadata VM)
        input=[
            "iqn.2015-05.com.oracle:QD_DG_VOTE101_EXAO2ADM1VM101 dm-7 IET,VIRTUAL-DISK",
            "size=128M features='0' hwhandler='0' wp=rw",
            "|-+- policy='round-robin 0' prio=0 status=active",
            "| `- 8:0:0:1  sdg  8:96   active undef unknown",
            "|-+- policy='round-robin 0' prio=0 status=enabled",
            "| `- 9:0:0:1  sdh  8:112  active undef unknown",
            "|-+- policy='round-robin 0' prio=0 status=enabled",
            "| `- 10:0:0:1 sdi  8:128  active undef unknown",
            "`-+- policy='round-robin 0' prio=0 status=enabled",
            "  `- 11:0:0:1 sdj  8:144  active undef unknown",
        ],
        output={
            "iqn.2015-05.com.oracle:QD_DG_VOTE101_EXAO2ADM1VM101": {
                "paths": ["sdg", "sdh", "sdi", "sdj"],
                "broken_paths": [],
                "luns": ["8:0:0:1(sdg)", "9:0:0:1(sdh)", "10:0:0:1(sdi)", "11:0:0:1(sdj)"],
                "uuid": "iqn.2015-05.com.oracle:QD_DG_VOTE101_EXAO2ADM1VM101",
                "state": "prio=0status=enabled",
                "numpaths": 4,
                "device": "dm-7",
            }
        },
    ),
]


@pytest.mark.parametrize("test_data", TEST_DATA, ids=[tt.input[0] for tt in TEST_DATA])
def test_parse_multipath(test_data: TupleTestData) -> None:
    check = Check("multipath")
    result = check.run_parse([re.split(" +", line.strip()) for line in test_data.input])
    assert test_data.output == result


@pytest.mark.parametrize(
    "group,result",
    [
        (
            ["iqn.2015-05.com.oracle:QD_DG_VOTE101_EXAO2ADM1VM101", "dm-7", "IET,VIRTUAL-DISK"],
            "iqn.2015-05.com.oracle:QD_DG_VOTE101_EXAO2ADM1VM101",
        ),
        (["1IET", "00010001", "dm-4", "IET,VIRTUAL-DISK"], "1IET 00010001"),
        (
            ["SDataCoreSANsymphony_DAT05-fscl", "dm-6", "DataCore,SANsymphony"],
            "SDataCoreSANsymphony_DAT05-fscl",
        ),
        (
            [
                "mpatha",
                "(HP_iLO_Internal_SD-CARD_000002660A01-0:0)",
                "dm-6",
                "HP",
                "iLO",
                ",Internal",
                "SD-CARD",
            ],
            "HP_iLO_Internal_SD-CARD_000002660A01-0:0",
        ),
        (["SDDN_S2A_9900_1308xxxxxxxx", "dm-13", "DDN,S2A", "9900"], "SDDN_S2A_9900_1308xxxxxxxx"),
        (
            ["3600508b40006d7da0001a00004740000", "dm-0", "HP,HSV210"],
            "3600508b40006d7da0001a00004740000",
        ),
        (
            ["360080e500017bd72000002eb4c1b1ae8", "dm-1", "IBM,1814", "FAStT"],
            "360080e500017bd72000002eb4c1b1ae8",
        ),
        (["mpath1", "(SIBM_____SwapA__________DA02BF71)"], "SIBM_____SwapA__________DA02BF71"),
        (
            ["anzvol1", "(36005076306ffc6480000000000005005)", "dm-16", "IBM,2107900"],
            "36005076306ffc6480000000000005005",
        ),
        (
            ["1494554000000000052303250303700000000000000000000", "dm-0", "IET,VIRTUAL-DISK"],
            "1494554000000000052303250303700000000000000000000",
        ),
        (
            ["360a980004334644d654a316e65306e51dm-4", "NETAPP,LUN"],
            "360a980004334644d654a316e65306e51",
        ),
        (["SFUJITSU_MAW3073NC_DBL2P62003VT"], "SFUJITSU_MAW3073NC_DBL2P62003VT"),
        (["360a980004334644d654a364469555a76"], "360a980004334644d654a364469555a76"),
        (
            ["orabase.lun50", "(360a9800043346937686f456f59386741)", "dm-15", "NETAPP,LUN"],
            "360a9800043346937686f456f59386741",
        ),
    ],
)
def test_multipath_parse_groups(group, result) -> None:
    check = Check("multipath")
    assert result in check.run_parse([group])
