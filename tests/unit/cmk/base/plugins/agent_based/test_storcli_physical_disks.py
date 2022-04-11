#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final

import pytest

from cmk.base.plugins.agent_based.storcli_physical_disks import parse_storcli_physical_disks
from cmk.base.plugins.agent_based.utils import megaraid

OUTPUT: Final = """
CLI Version = 007.0709.0000.0000 Aug 14, 2018
Operating system = Linux 5.4.0-87-generic
Controller = 0
Status = Success
Description = Show Drive Information Succeeded.


Drive /c0/e252/s0 :
=================

---------------------------------------------------------------------------------
EID:Slt DID State DG       Size Intf Med SED PI SeSz Model               Sp Type
---------------------------------------------------------------------------------
252:0     4 Onln   0 666.666 GB SATA SSD N   N  512B INTEL SSDSC2KB480G8 U  -
---------------------------------------------------------------------------------

EID-Enclosure Device ID|Slt-Slot No.|DID-Device ID|DG-DriveGroup
DHS-Dedicated Hot Spare|UGood-Unconfigured Good|GHS-Global Hotspare
UBad-Unconfigured Bad|Onln-Online|Offln-Offline|Intf-Interface
Med-Media Type|SED-Self Encryptive Drive|PI-Protection Info
SeSz-Sector Size|Sp-Spun|U-Up|D-Down/PowerSave|T-Transition|F-Foreign
UGUnsp-Unsupported|UGShld-UnConfigured shielded|HSPShld-Hotspare shielded
CFShld-Configured shielded|Cpybck-CopyBack|CBShld-Copyback Shielded


Drive /c0/e252/s0 - Detailed Information :
========================================

Drive /c0/e252/s0 State :
=======================
Shield Counter = 0
Media Error Count = 0
Other Error Count = 0
Drive Temperature =  22C (71.60 F)
Predictive Failure Count = 0
S.M.A.R.T alert flagged by drive = No


Drive /c0/e252/s0 Device attributes :
===================================
SN = BTYFXXXXXXXXXXXBGN
Manufacturer Id = ATA
Model Number = INTEL SSDSC2KB480G8
NAND Vendor = NA
WWN = 55DEADBEEF666666
Firmware Revision = XCV10100
Raw size = 447.130 GB [0x37e436b0 Sectors]
Coerced size = 446.102 GB [0x37c34800 Sectors]
Non Coerced size = 446.630 GB [0x37d436b0 Sectors]
Device Speed = 6.0Gb/s
Link Speed = 6.0Gb/s
NCQ setting = Enabled
Write Cache = N/A
Logical Sector Size = 512B
Physical Sector Size = 4 KB
Connector Name = Port 0 - 3 x1


Drive /c0/e252/s0 Policies/Settings :
===================================
Drive position = DriveGroup:0, Span:0, Row:0
Enclosure position = 1
Connected Port Number = 1(path0)
Sequence Number = 2
Commissioned Spare = No
Emergency Spare = No
Last Predictive Failure Event Sequence Number = 0
Successful diagnostics completion on = N/A
FDE Type = None
SED Capable = No
SED Enabled = No
Secured = No
Cryptographic Erase Capable = Yes
Locked = No
Needs EKM Attention = No
PI Eligible = No
Certified = No
Wide Port Capable = No
Unmap capable = No

Port Information :
================

-----------------------------------------
Port Status Linkspeed SAS address
-----------------------------------------
   0 Active 6.0Gb/s   0x4433221103000000
-----------------------------------------


Inquiry Data =
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00



Drive /c0/e252/s1 :
=================

---------------------------------------------------------------------------------
EID:Slt DID State DG       Size Intf Med SED PI SeSz Model               Sp Type
---------------------------------------------------------------------------------
252:1     5 Onln   0 666.666 GB SATA SSD N   N  512B INTEL SSDSC2KB480G8 U  -
---------------------------------------------------------------------------------

EID-Enclosure Device ID|Slt-Slot No.|DID-Device ID|DG-DriveGroup
DHS-Dedicated Hot Spare|UGood-Unconfigured Good|GHS-Global Hotspare
UBad-Unconfigured Bad|Onln-Online|Offln-Offline|Intf-Interface
Med-Media Type|SED-Self Encryptive Drive|PI-Protection Info
SeSz-Sector Size|Sp-Spun|U-Up|D-Down/PowerSave|T-Transition|F-Foreign
UGUnsp-Unsupported|UGShld-UnConfigured shielded|HSPShld-Hotspare shielded
CFShld-Configured shielded|Cpybck-CopyBack|CBShld-Copyback Shielded


Drive /c0/e252/s1 - Detailed Information :
========================================

Drive /c0/e252/s1 State :
=======================
Shield Counter = 0
Media Error Count = 0
Other Error Count = 0
Drive Temperature =  22C (71.60 F)
Predictive Failure Count = 0
S.M.A.R.T alert flagged by drive = No


Drive /c0/e252/s1 Device attributes :
===================================
SN = BTYXXXXXXXXXXXXBGN
Manufacturer Id = ATA
Model Number = INTEL SSDSC2KB480G8
NAND Vendor = NA
WWN = 55DEADBEEF666666
Firmware Revision = XCV10120
Raw size = 447.130 GB [0x37e436b0 Sectors]
Coerced size = 446.102 GB [0x37c34800 Sectors]
Non Coerced size = 446.630 GB [0x37d436b0 Sectors]
Device Speed = 6.0Gb/s
Link Speed = 6.0Gb/s
NCQ setting = Enabled
Write Cache = N/A
Logical Sector Size = 512B
Physical Sector Size = 4 KB
Connector Name = Port 0 - 3 x1


Drive /c0/e252/s1 Policies/Settings :
===================================
Drive position = DriveGroup:0, Span:0, Row:1
Enclosure position = 1
Connected Port Number = 2(path0)
Sequence Number = 2
Commissioned Spare = No
Emergency Spare = No
Last Predictive Failure Event Sequence Number = 0
Successful diagnostics completion on = N/A
FDE Type = None
SED Capable = No
SED Enabled = No
Secured = No
Cryptographic Erase Capable = Yes
Locked = No
Needs EKM Attention = No
PI Eligible = No
Certified = No
Wide Port Capable = No
Unmap capable = No

Port Information :
================

-----------------------------------------
Port Status Linkspeed SAS address
-----------------------------------------
   0 Active 6.0Gb/s   0x4433221102000000
-----------------------------------------


Inquiry Data =
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00



Drive /c0/e252/s2 :
=================

-----------------------------------------------------------------------------
EID:Slt DID State DG      Size Intf Med SED PI SeSz Model            Sp Type
-----------------------------------------------------------------------------
252:2     8 Onln   1 10.912 TB SAS  HDD N   N  512B HUH721212AL5200  U  -
-----------------------------------------------------------------------------

EID-Enclosure Device ID|Slt-Slot No.|DID-Device ID|DG-DriveGroup
DHS-Dedicated Hot Spare|UGood-Unconfigured Good|GHS-Global Hotspare
UBad-Unconfigured Bad|Onln-Online|Offln-Offline|Intf-Interface
Med-Media Type|SED-Self Encryptive Drive|PI-Protection Info
SeSz-Sector Size|Sp-Spun|U-Up|D-Down/PowerSave|T-Transition|F-Foreign
UGUnsp-Unsupported|UGShld-UnConfigured shielded|HSPShld-Hotspare shielded
CFShld-Configured shielded|Cpybck-CopyBack|CBShld-Copyback Shielded


Drive /c0/e252/s2 - Detailed Information :
========================================

Drive /c0/e252/s2 State :
=======================
Shield Counter = 0
Media Error Count = 0
Other Error Count = 0
Drive Temperature =  28C (82.40 F)
Predictive Failure Count = 0
S.M.A.R.T alert flagged by drive = No


Drive /c0/e252/s2 Device attributes :
===================================
SN = XXXXXXXX
Manufacturer Id = HGST
Model Number = HUHXXXXXXXXX200
NAND Vendor = NA
WWN = 50DEADBEEF666666
Firmware Revision = A925
Firmware Release Number = N/A
Raw size = 10.914 TB [0x575000000 Sectors]
Coerced size = 10.912 TB [0x574de1000 Sectors]
Non Coerced size = 10.913 TB [0x574f00000 Sectors]
Device Speed = 12.0Gb/s
Link Speed = 12.0Gb/s
Write Cache = N/A
Logical Sector Size = 512B
Physical Sector Size = 4 KB
Connector Name = Port 0 - 3 x1


Drive /c0/e252/s2 Policies/Settings :
===================================
Drive position = DriveGroup:1, Span:0, Row:1
Enclosure position = 1
Connected Port Number = 3(path0)
Sequence Number = 2
Commissioned Spare = No
Emergency Spare = No
Last Predictive Failure Event Sequence Number = 0
Successful diagnostics completion on = N/A
FDE Type = None
SED Capable = No
SED Enabled = No
Secured = No
Cryptographic Erase Capable = Yes
Locked = No
Needs EKM Attention = No
PI Eligible = No
Certified = No
Wide Port Capable = No
Unmap capable = No

Port Information :
================

-----------------------------------------
Port Status Linkspeed SAS address
-----------------------------------------
   0 Active 12.0Gb/s  0x5000cca2914ab819
   1 Active 12.0Gb/s  0x0
-----------------------------------------


Inquiry Data =
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00



Drive /c0/e252/s3 :
=================

-----------------------------------------------------------------------------
EID:Slt DID State DG      Size Intf Med SED PI SeSz Model            Sp Type
-----------------------------------------------------------------------------
252:3     9 Onln   1 10.912 TB SAS  HDD N   N  512B HUH721212AL5200  U  -
-----------------------------------------------------------------------------

EID-Enclosure Device ID|Slt-Slot No.|DID-Device ID|DG-DriveGroup
DHS-Dedicated Hot Spare|UGood-Unconfigured Good|GHS-Global Hotspare
UBad-Unconfigured Bad|Onln-Online|Offln-Offline|Intf-Interface
Med-Media Type|SED-Self Encryptive Drive|PI-Protection Info
SeSz-Sector Size|Sp-Spun|U-Up|D-Down/PowerSave|T-Transition|F-Foreign
UGUnsp-Unsupported|UGShld-UnConfigured shielded|HSPShld-Hotspare shielded
CFShld-Configured shielded|Cpybck-CopyBack|CBShld-Copyback Shielded


Drive /c0/e252/s3 - Detailed Information :
========================================

Drive /c0/e252/s3 State :
=======================
Shield Counter = 0
Media Error Count = 0
Other Error Count = 0
Drive Temperature =  28C (82.40 F)
Predictive Failure Count = 0
S.M.A.R.T alert flagged by drive = No


Drive /c0/e252/s3 Device attributes :
===================================
SN = XXXXXXXX
Manufacturer Id = HGST
Model Number = HUH721212AL5200
NAND Vendor = NA
WWN = 5000CCA2B0046E57
Firmware Revision = A925
Firmware Release Number = N/A
Raw size = 10.914 TB [0x575000000 Sectors]
Coerced size = 10.912 TB [0x574de1000 Sectors]
Non Coerced size = 10.913 TB [0x574f00000 Sectors]
Device Speed = 12.0Gb/s
Link Speed = 12.0Gb/s
Write Cache = N/A
Logical Sector Size = 512B
Physical Sector Size = 4 KB
Connector Name = Port 0 - 3 x1


Drive /c0/e252/s3 Policies/Settings :
===================================
Drive position = DriveGroup:1, Span:0, Row:0
Enclosure position = 1
Connected Port Number = 0(path0)
Sequence Number = 2
Commissioned Spare = No
Emergency Spare = No
Last Predictive Failure Event Sequence Number = 0
Successful diagnostics completion on = N/A
FDE Type = None
SED Capable = No
SED Enabled = No
Secured = No
Cryptographic Erase Capable = Yes
Locked = No
Needs EKM Attention = No
PI Eligible = No
Certified = No
Wide Port Capable = No
Unmap capable = No

Port Information :
================

-----------------------------------------
Port Status Linkspeed SAS address
-----------------------------------------
   0 Active 12.0Gb/s  0x5000cca2b0046e55
   1 Active 12.0Gb/s  0x0
-----------------------------------------


Inquiry Data =
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00

"""


STRING_TABLE: Final = [line.split() for line in OUTPUT.splitlines() if line]


@pytest.fixture(scope="module", name="section")
def _get_section() -> megaraid.SectionPDisks:
    return parse_storcli_physical_disks(STRING_TABLE)


def test_parse_storcli_physical_disks(section: megaraid.SectionPDisks) -> None:
    assert section == {
        "/c0/e252/s0": megaraid.PDisk(
            name="/c0/e252/s0",
            state="Online",
            failures=0,
        ),
        "/c0/e252/s1": megaraid.PDisk(
            name="/c0/e252/s1",
            state="Online",
            failures=0,
        ),
        "/c0/e252/s2": megaraid.PDisk(
            name="/c0/e252/s2",
            state="Online",
            failures=0,
        ),
        "/c0/e252/s3": megaraid.PDisk(
            name="/c0/e252/s3",
            state="Online",
            failures=0,
        ),
    }
