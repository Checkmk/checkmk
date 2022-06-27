#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final

import pytest

from cmk.base.plugins.agent_based.storcli_virtual_disks import parse_storcli_virtual_disks
from cmk.base.plugins.agent_based.utils import megaraid

OUTPUT: Final = """
CLI Version = 007.0709.0000.0000 Aug 14, 2018
Operating system = Linux 5.4.0-87-generic
Controller = 0
Status = Success
Description = Show Drive Information Succeeded.


/c0/v0 :
======

--------------------------------------------------------------
DG/VD TYPE  State Access Consist Cache Cac sCC      Size Name
--------------------------------------------------------------
0/0   RAID6 Optl  RW     Yes     RWBC  -   OFF 99.996 GB
--------------------------------------------------------------

[ some lines that don't matter ]

PDs for VD 0 :
============

[ some lines that don't matter ]

VD0 Properties :
==============
Strip Size = 256 KB
Number of Blocks = 209707008
VD has Emulated PD = Yes
Span Depth = 1
Number of Drives Per Span = 23
Write Cache(initial setting) = WriteBack
Disk Cache Policy = Disabled
Encryption = None
Data Protection = Disabled
Active Operations = None
Exposed to OS = Yes
OS Drive Name = /dev/sda
Creation Date = 26-01-2022
Creation Time = 07:03:05 AM
Emulation type = default
Cachebypass size = Cachebypass-64k
Cachebypass Mode = Cachebypass Intelligent
Is LD Ready for OS Requests = Yes
SCSI NAA Id = 600e0004001e49902983aea95aad0556


/c0/v1 :
======

--------------------------------------------------------------
DG/VD TYPE  State Access Consist Cache Cac sCC      Size Name
--------------------------------------------------------------
0/1   RAID6 Optl  RW     Yes     RWBC  -   OFF 45.738 TB
--------------------------------------------------------------

PDs for VD 1 :
============

[ some lines that don't matter ]

VD1 Properties :
==============
Strip Size = 256 KB
Number of Blocks = 98224250880
VD has Emulated PD = Yes
Span Depth = 1
Number of Drives Per Span = 23
Write Cache(initial setting) = WriteBack
Disk Cache Policy = Disabled
Encryption = None
Data Protection = Disabled
Active Operations = None
Exposed to OS = Yes
OS Drive Name = /dev/sdb
Creation Date = 26-01-2022
Creation Time = 07:03:07 AM
Emulation type = default
Cachebypass size = Cachebypass-64k
Cachebypass Mode = Cachebypass Intelligent
Is LD Ready for OS Requests = Yes
SCSI NAA Id = 600e0004001e49902983aeab5ad3be10


"""


STRING_TABLE: Final = [line.split() for line in OUTPUT.splitlines() if line]


@pytest.fixture(scope="module", name="section")
def _get_section() -> megaraid.SectionLDisks:
    return parse_storcli_virtual_disks(STRING_TABLE)


def test_parse_storcli_virtualal_disks(section: megaraid.SectionLDisks) -> None:
    assert section == {
        "/c0/v0": megaraid.LDisk(
            state="Optimal",
        ),
        "/c0/v1": megaraid.LDisk(
            state="Optimal",
        ),
    }
