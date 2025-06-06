#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translations

translation_esx_vsphere_vm_mem_usage = translations.Translation(
    name="esx_vsphere_vm_mem_usage",
    check_commands=[translations.PassiveCheck("esx_vsphere_vm_mem_usage")],
    translations={
        "ballooned": translations.RenameTo("mem_esx_ballooned"),
        "guest": translations.RenameTo("mem_esx_guest"),
        "host": translations.RenameTo("mem_esx_host"),
        "private": translations.RenameTo("mem_esx_private"),
        "shared": translations.RenameTo("mem_esx_shared"),
    },
)
