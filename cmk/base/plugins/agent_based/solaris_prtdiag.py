#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# [['System Configuration:  Sun Microsystems  sun4u SPARC Enterprise M4000 Server'],
#  ['System clock frequency: 1012 MHz'],
#  ['Memory size: 262144 Megabytes'],
#  ['==================================== CPUs ===================================='],
#  ['CPU                 CPU                         Run    L2$    CPU   CPU'],
#  ['LSB   Chip                 ID                         MHz     MB    Impl. Mask'],
#  ['---   ----  ----------------------------------------  ----   ---    ----- ----'],
#  ['00     0      0,   1,   2,   3,   4,   5,   6,   7   2660  11.0        7  193'],
#  ['00     1      8,   9,  10,  11,  12,  13,  14,  15   2660  11.0        7  193'],
#  ['00     2     16,  17,  18,  19,  20,  21,  22,  23   2660  11.0        7  193'],
#  ['00     3     24,  25,  26,  27,  28,  29,  30,  31   2660  11.0        7  193'],
#  ['============================ Memory Configuration ============================'],
#  ['Memory  Available           Memory     DIMM    # of  Mirror  Interleave'],
#  ['LSB    Group   Size                Status     Size    DIMMs Mode    Factor'],
#  ['---    ------  ------------------  -------    ------  ----- ------- ----------'],
#  ['00    A       131072MB            okay       8192MB     16 no       8-way'],
#  ['00    B       131072MB            okay       8192MB     16 no       8-way'],
#  ['========================= IO Devices ========================='],
#  ['IO                                                Lane/Frq'],
#  ['LSB Type  LPID   RvID,DvID,VnID       BDF       State Act,  Max   Name                           Model'],
#  ['--- ----- ----   ------------------   --------- ----- ----------- ------------------------------ --------------------'],
#  ['Logical Path'],
#  ['------------'],
#  ['00  PCIe  0      bc, 8532, 10b5       2,  0,  0  okay     8,    8  pci-pciexclass,060400          N/A'],
#  ['/pci@0,600000/pci@0'],
#  ['00  PCIe  0      bc, 8532, 10b5       3,  8,  0  okay     8,    8  pci-pciexclass,060400          N/A'],
#  ['/pci@0,600000/pci@0/pci@8'],
#  ['00  PCIe  0      bc, 8532, 10b5       3,  9,  0  okay     1,    8  pci-pciexclass,060400          N/A'],
#  ['/pci@0,600000/pci@0/pci@9'],
#  ['00  PCIx  0       8,  125, 1033       4,  0,  0  okay   100,  133  pci-pciexclass,060400          N/A'],
#  ['/pci@0,600000/pci@0/pci@8/pci@0'],
#  ['00  PCIx  0       8,  125, 1033       4,  0,  1  okay    --,  133  pci-pciexclass,060400          N/A'],
#  ['/pci@0,600000/pci@0/pci@8/pci@0,1'],
#  ['00  PCIx  0       2,   50, 1000       5,  1,  0  okay    --,  133  scsi-pci1000,50                LSI,1064'],
#  ['/pci@0,600000/pci@0/pci@8/pci@0/scsi@1'],
#  ['00  PCIx  0      10, 1648, 14e4       5,  2,  0  okay    --,  133  network-pci14e4,1648           N/A'],
#  ['/pci@0,600000/pci@0/pci@8/pci@0/network@2'],
#  ['00  PCIx  0      10, 1648, 14e4       5,  2,  1  okay    --,  133  network-pci14e4,1648           N/A'],
#  ['/pci@0,600000/pci@0/pci@8/pci@0/network@2,1'],
#  ['00  PCIe  1       1, abcd, 108e       2,  0,  0  okay     8,    8  network-pciex108e,abcd         SUNW,pcie-qgc'],
#  ['/pci@1,700000/network@0'],
#  ['00  PCIe  1       1, abcd, 108e       2,  0,  1  okay     8,    8  network-pciex108e,abcd         SUNW,pcie-qgc'],
#  ['/pci@1,700000/network@0,1'],
#  ['00  PCIe  1       1, abcd, 108e       2,  0,  2  okay     8,    8  network-pciex108e,abcd         SUNW,pcie-qgc'],
#  ['/pci@1,700000/network@0,2'],
#  ['00  PCIe  1       1, abcd, 108e       2,  0,  3  okay     8,    8  network-pciex108e,abcd         SUNW,pcie-qgc'],
#  ['/pci@1,700000/network@0,3'],
#  ['00  PCIe  2       2, 2532, 1077       2,  0,  0  okay     8,    8  SUNW,qlc-pciex1077,2532        QLE2560'],
#  ['/pci@2,600000/SUNW,qlc@0'],
#  ['00  PCIe  3       2, 2532, 1077       2,  0,  0  okay     8,    8  SUNW,qlc-pciex1077,2532        QLE2560'],
#  ['/pci@3,700000/SUNW,qlc@0'],
#  ['==================== Hardware Revisions ===================='],
#  ['System PROM revisions:'],
#  ['----------------------'],
#  ['OBP 4.24.16 2010/12/10 01:37'],
#  ['=================== Environmental Status ==================='],
#  ['Mode switch is in LOCK mode'],
#  ['=================== System Processor Mode ==================='],
#  ['SPARC64-VII mode']]
#

import time
from typing import Mapping, NamedTuple, Union

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


class Section(NamedTuple):
    bios: Mapping[str, Union[str, int]]
    hardware: Mapping[str, str]


def parse_solaris_prtdiag(string_table: StringTable) -> Section:
    bios: dict[str, Union[str, int]] = {}
    hardware = {}
    for line in string_table:
        if line[0].startswith("OBP"):
            bios_info = line[0].split()
            bios["version"] = "%s %s" % (bios_info[0], bios_info[1])
            formated_date = bios_info[2] + bios_info[3]
            bios["date"] = int(time.mktime(time.strptime(formated_date, "%Y/%m/%d%H:%M")))
            bios["vendor"] = "Oracle"

        elif line[0].startswith("SerialNumber:"):
            hardware["serial"] = line[0].split(":")[1]

        elif line[0].startswith("System Configuration:"):
            # 'System Configuration:  Oracle Corporation  sun4v SPARC T4-1'
            # 'System Configuration:  Sun Microsystems  sun4u SPARC Enterprise M4000 Server'
            # 'System Configuration: Supermicro H8DG6/H8DGi'
            # 'System Configuration: Oracle Corporation SUN FIRE X4170 M2 SERVER'
            # 'System Configuration: Sun Microsystems     Sun Fire X4540'
            # 'System Configuration: VMware, Inc. VMware Virtual Platform'
            # 'System Configuration: HP ProLiant DL380 G5'
            # 'System Configuration: SUN MICROSYSTEMS SUN FIRE X4270 SERVER'
            # 'System Configuration: Sun Microsystems SUN FIRE X4450'
            system_info = (
                line[0].split(":", 1)[1].strip().replace("SERVER", "").replace("Server", "")
            )

            if "sun microsystems" in system_info.lower():
                vendor = "Sun Microsystems"
                index = 2
            elif "oracle corporation" in system_info.lower():
                vendor = "Oracle Corporation"
                index = 2
            elif "supermicro" in system_info.lower():
                vendor = "Supermicro"
                index = 1
            elif "vmware, inc." in system_info.lower():
                vendor = "VMWare, Inc."
                index = 2
            elif "hp" in system_info.lower():
                vendor = "HP"
                index = 1
            else:
                vendor = system_info.split(" ")[0]
                index = 1

            system_info = " ".join(system_info.split(" ")[index:]).strip()
            hardware["vendor"] = vendor

            if "sun fire" in system_info.lower():
                index = 3
            elif "sun4u" in system_info.lower() or "proliant" in system_info.lower():
                index = 2
            elif "vmware" in system_info.lower():
                index = 3
            else:
                index = 1

            hardware["product"] = " ".join(system_info.split(" ")[:index])
            family = " ".join(system_info.split(" ")[index:])

            if family:
                hardware["family"] = "%s-series" % family[0].upper()

    return Section(bios=bios, hardware=hardware)


register.agent_section(
    name="solaris_prtdiag",
    parse_function=parse_solaris_prtdiag,
)


def inventory_solaris_prtdiag(section: Section) -> InventoryResult:
    yield Attributes(
        path=["software", "bios"],
        inventory_attributes=section.bios,
    )
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes=section.hardware,
    )


register.inventory_plugin(
    name="solaris_prtdiag",
    inventory_function=inventory_solaris_prtdiag,
)
