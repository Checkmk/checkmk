#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.broadcom_storage.agent_based.storcli_pdisks import (
    check_storcli_pdisks,
    parse_storcli_pdisks,
    StorcliPDisk,
)
from cmk.plugins.broadcom_storage.lib import megaraid

# agent_output/CMK-7584-storcli_pdisks
SECTION_V1 = """CLI Version = 007.1017.0000.0000 May 10, 2019
Operating system = Windows Server 2012 R2
Controller = 0
Status = Success
Description = Show Drive Information Succeeded.


Drive Information :
=================

-------------------------------------------------------------------------------------
EID:Slt DID State DG       Size Intf Med SED PI SeSz Model                   Sp Type
-------------------------------------------------------------------------------------
8:0      15 Onln   0 953.343 GB SATA SSD N   N  512B Samsung SSD 850 PRO 1TB U  -
8:1      23 Onln   0 953.343 GB SATA SSD N   N  512B Samsung SSD 850 PRO 1TB U  -
8:2      18 Onln   0 953.343 GB SATA SSD N   N  512B Samsung SSD 850 PRO 1TB U  -
8:3      21 Onln   1   5.457 TB SATA HDD N   N  512B ST6000000000-111111     U  -
8:4      10 Onln   1   5.457 TB SATA HDD N   N  512B ST6000000000-111111     U  -
8:5      14 Onln   1   5.457 TB SATA HDD N   N  512B ST6000000000-111111     U  -
8:6      17 Onln   1   5.457 TB SATA HDD N   N  512B ST6000000000-111111     U  -
8:7      20 Onln   1   5.457 TB SATA HDD N   N  512B ST6000000000-111111     U  -
8:8       9 Onln   1   5.457 TB SATA HDD N   N  512B ST6000000000-111111     U  -
-------------------------------------------------------------------------------------

EID=Enclosure Device ID|Slt=Slot No.|DID=Device ID|DG=DriveGroup
DHS=Dedicated Hot Spare|UGood=Unconfigured Good|GHS=Global Hotspare
UBad=Unconfigured Bad|Onln=Online|Offln=Offline|Intf=Interface
Med=Media Type|SED=Self Encryptive Drive|PI=Protection Info
SeSz=Sector Size|Sp=Spun|U=Up|D=Down|T=Transition|F=Foreign
UGUnsp=Unsupported|UGShld=UnConfigured shielded|HSPShld=Hotspare shielded
CFShld=Configured shielded|Cpybck=CopyBack|CBShld=Copyback Shielded
UBUnsp=UBad Unsupported



"""

# SUP-22144
SECTION_V2 = """CLI Version = 008.0011.0000.0014 Sep 26, 2024
Operating system = Windows Server 2022
Controller = 0
Status = Success
Description = Show Drive Information Succeeded.


Drive Information :
=================

-------------------------------------------------------------------------------------------------------------------------------
EID:Slt PID State Status DG        Size Intf Med SED_Type SeSz Model                                    Sp LU/NS Count Alt-EID
-------------------------------------------------------------------------------------------------------------------------------
308:0   283 Conf  Online  0 223.062 GiB SATA SSD Opal     512B SAMSUNG MZ7777777777-00000               U            1 -
308:4   287 Conf  Online  0 223.062 GiB SATA SSD Opal     512B SAMSUNG MZ7777777777-00000               U            1 -
308:8   291 Conf  Online  1   6.985 TiB NVMe SSD Opal     512B SAMSUNG MZQQQQQQQQQQ-00000               U            1 -
308:12  292 Conf  Online  1   6.985 TiB NVMe SSD Opal     512B SAMSUNG MZQQQQQQQQQQ-00000               U            1 -
308:16  293 Conf  Online  1   6.985 TiB NVMe SSD Opal     512B SAMSUNG MZQQQQQQQQQQ-00000               U            1 -
308:20  294 Conf  Online  1   6.985 TiB NVMe SSD Opal     512B SAMSUNG MZQQQQQQQQQQ-00000               U            1 -
-------------------------------------------------------------------------------------------------------------------------------


LU/NS Information :
=================

--------------------------------------
PID LUN/NSID Index Status        Size
--------------------------------------
283 0/-          0 Online 223.062 GiB
287 0/-          0 Online 223.062 GiB
291 0/1          0 Online   6.985 TiB
292 0/1          0 Online   6.985 TiB
293 0/1          0 Online   6.985 TiB
294 0/1          0 Online   6.985 TiB
--------------------------------------

EID-Enclosure Persistent ID|Slt-Slot Number|PID-Persistent ID|DG-DriveGroup
UConf-Unconfigured|UConfUnsp-Unconfigured Unsupported|Conf-Configured|Unusbl-Unusable
GHS-Global Hot Spare|DHS-Dedicated Hot Spare|UConfShld-Unconfigured Shielded|
ConfShld-Configured Shielded|Shld-JBOD Shielded|GHSShld-GHS Shielded|DHSShld-DHS Shielded
UConfSntz-Unconfigured Sanitize|ConfSntz-Configured Sanitize|JBODSntz-JBOD Sanitize|GHSSntz-GHS Sanitize
DHSSntz-DHS Sanitize|UConfDgrd-Unconfigured Degraded|ConfDgrd-Configured Degraded|JBODDgrd-JBOD Degraded
GHSDgrd-GHS Degraded|DHSDgrd-DHS Degraded|Various-Multiple LU/NS Status|Med-Media|SED-Self Encryptive Drive
SeSz-Logical Sector Size|Intf-Interface|Sp-Power state|U-Up/On|D-Down/PowerSave|T-Transitioning|F-Foreign
NS-Namespace|LU-Logical Unit|LUN-Logical Unit Number|NSID-Namespace ID|Alt-EID-Alternate Enclosure Persistent ID



"""


# SUP-23147
SECTION_V3 = """CLI Version = 007.3205.0000.0000 Oct 09, 2024
Operating system = Windows Server 2019
Controller = 0
Status = Success
Description = Show Drive Information Succeeded.


Drive Information :
=================

-----------------------------------------------------------------------------------
EID:Slt DID State DG Size Intf Med SED PI SeSz Model Sp Type
-----------------------------------------------------------------------------------
8:0 10 JBOD - 10.914 TB SATA HDD N N 512B TOSHIBA MG07ACA12TE U -
8:1 15 JBOD - 10.914 TB SATA HDD N N 512B ST12000VN0008-2YS101 U -
8:2 11 JBOD - 10.914 TB SATA HDD N N 512B TOSHIBA MG07ACA12TE U -
8:3 17 JBOD - 10.914 TB SATA HDD N N 512B TOSHIBA MG07ACA12TE U -
9:10 36 Onln 0 931.000 GB SATA HDD N N 512B ST1000NM0008-2F2100 U -
9:11 34 Onln 0 931.000 GB SATA HDD N N 512B ST1000NM0008-2F2100 U -
-----------------------------------------------------------------------------------

EID=Enclosure Device ID|Slt=Slot No|DID=Device ID|DG=DriveGroup
DHS=Dedicated Hot Spare|UGood=Unconfigured Good|GHS=Global Hotspare
UBad=Unconfigured Bad|Sntze=Sanitize|Onln=Online|Offln=Offline|Intf=Interface
Med=Media Type|SED=Self Encryptive Drive|PI=PI Eligible
SeSz=Sector Size|Sp=Spun|U=Up|D=Down|T=Transition|F=Foreign
UGUnsp=UGood Unsupported|UGShld=UGood shielded|HSPShld=Hotspare shielded
CFShld=Configured shielded|Cpybck=CopyBack|CBShld=Copyback Shielded
UBUnsp=UBad Unsupported|Rbld=Rebuild



"""


def _to_string_table(raw: str) -> StringTable:
    return [list(re.split(" +", line.strip())) for line in raw.strip().split("\n") if line]


def test_parse_v1():
    assert parse_storcli_pdisks(_to_string_table(SECTION_V1)) == {
        "C0.8:0-15": StorcliPDisk(size=(953.343, "GB"), state="Online"),
        "C0.8:1-23": StorcliPDisk(size=(953.343, "GB"), state="Online"),
        "C0.8:2-18": StorcliPDisk(size=(953.343, "GB"), state="Online"),
        "C0.8:3-21": StorcliPDisk(size=(5.457, "TB"), state="Online"),
        "C0.8:4-10": StorcliPDisk(size=(5.457, "TB"), state="Online"),
        "C0.8:5-14": StorcliPDisk(size=(5.457, "TB"), state="Online"),
        "C0.8:6-17": StorcliPDisk(size=(5.457, "TB"), state="Online"),
        "C0.8:7-20": StorcliPDisk(size=(5.457, "TB"), state="Online"),
        "C0.8:8-9": StorcliPDisk(size=(5.457, "TB"), state="Online"),
    }


def test_parse_v2():
    assert parse_storcli_pdisks(_to_string_table(SECTION_V2)) == {
        "C0.308:0-283": StorcliPDisk(state="Conf", size=(223.062, "GiB")),
        "C0.308:4-287": StorcliPDisk(state="Conf", size=(223.062, "GiB")),
        "C0.308:8-291": StorcliPDisk(state="Conf", size=(6.985, "TiB")),
        "C0.308:12-292": StorcliPDisk(state="Conf", size=(6.985, "TiB")),
        "C0.308:16-293": StorcliPDisk(state="Conf", size=(6.985, "TiB")),
        "C0.308:20-294": StorcliPDisk(state="Conf", size=(6.985, "TiB")),
    }


def test_parse_v3():
    assert parse_storcli_pdisks(_to_string_table(SECTION_V3)) == {
        "C0.8:0-10": StorcliPDisk(size=(10.914, "TB"), state="JBOD"),
        "C0.8:1-15": StorcliPDisk(size=(10.914, "TB"), state="JBOD"),
        "C0.8:2-11": StorcliPDisk(size=(10.914, "TB"), state="JBOD"),
        "C0.8:3-17": StorcliPDisk(size=(10.914, "TB"), state="JBOD"),
        "C0.9:10-36": StorcliPDisk(size=(931, "GB"), state="Online"),
        "C0.9:11-34": StorcliPDisk(size=(931, "GB"), state="Online"),
    }


def test_check_simple() -> None:
    result = list(
        check_storcli_pdisks(
            item="C0.8:2-18",
            params=megaraid.PDISKS_DEFAULTS,
            section=parse_storcli_pdisks(
                _to_string_table(SECTION_V1),
            ),
        )
    )
    assert result == [
        Result(state=State.OK, summary="Size: 953.343 GB, Disk State: Online"),
    ]


def test_check_jbod() -> None:
    result = list(
        check_storcli_pdisks(
            item="C0.8:0-10",
            params=megaraid.PDISKS_DEFAULTS,
            section=parse_storcli_pdisks(
                _to_string_table(SECTION_V3),
            ),
        )
    )
    assert result == [
        Result(state=State.OK, summary="Size: 10.914 TB, Disk State: JBOD"),
    ]
