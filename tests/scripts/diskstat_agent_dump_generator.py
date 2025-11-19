#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Override `Disk IO summary` / `diskstat` service.

By adding a `datasource` program in a Checkmk site.
The script is meant for manual testing purposes only.
It can be used to perform system-level tests on how `Disk IO summary` service is handled
and populated by Chekcmk site.
"""

import time

# uncomment & adapt depending on use-case
DMSETUP_INFO = (
    ""
    #    "[dmsetup_info]\n"
    #    "vg0-root 252:0 vg0 root\n"
    #    "vg0-var 252:1 vg0 var"
    #    "vg0-opt 252:2 vg0 opt\n"
    #    "vg0-swap 252:3 vg0 swap\n"
)

ADDITIONAL_DATA = (
    "252 0 dm-0 50198 0 2312711 35525 7802064 0 175926546 8526391 0 1276942 9495402 12079 0 595319808 933486 0 0\n"
    "252 1 dm-1 1982902 0 73256424 1087150 28109797 0 1751853243 35509229 0 56925552 37664043 25965 0 328862240 1067664 0 0\n"
    "252 2 dm-2 3083 0 413495 2359 289529 0 7565370 363544 0 125649 595890 3438 0 177861224 229987 0 0\n"
    "252 3 dm-3 944 0 18024 617 4061 0 32488 19306 0 970 19923 0 0 0 0 0 0"
)


# uncomment and adapt depending on use-case
DEVICE_WWN = (
    "[device_wwn]\ninvalid data"
    # valid data
    # "[device_wwn]\nnvme-eui.00000000000000008ce38e1000e4b0f9 /dev/nvme0n1"
)

AGENT_OUTPUT = f"""
<<<diskstat>>>
{int(time.time())}
    8 0 sda 16672398 628689 1673318735 15675169 57170214 30952188 1479113320 7331377 0 2630351 23006546 0 0 0 0 0 0
    {ADDITIONAL_DATA if DMSETUP_INFO else ""}
{DMSETUP_INFO}
{DEVICE_WWN}
<<<local>>>
0 service-1 state=91 2025-11-18 16:44:27.395624 state: 91%
"""

print(AGENT_OUTPUT)
