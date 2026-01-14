#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

# Example output:
# <<<vxvm_objstatus>>>
# v datadg lalavol CLEAN DISABLED
# v datadg oravol ACTIVE ENABLED
# v datadg oravol-L01 ACTIVE ENABLED
# v datadg oravol-L02 ACTIVE ENABLED
# v testgroup oravol-L02 ACTIVE ENABLED


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def vxvm_objstatus_disks(info):
    groups = {}
    found_groups = []
    for dg_type, dg_name, name, admin_state, kernel_state in info:
        if dg_type == "v":
            if dg_name not in found_groups:
                groups[dg_name] = [(name, admin_state, kernel_state)]
                found_groups.append(dg_name)
            else:
                groups[dg_name].append((name, admin_state, kernel_state))
    return groups


def discover_vxvm_objstatus(info):
    return [(k, {}) for k in vxvm_objstatus_disks(info)]


def check_vxvm_objstatus(item, _no_params, info):
    groups = vxvm_objstatus_disks(info)
    volumes = groups.get(item)
    if volumes is not None:
        state = 0
        messages = []
        for volume, admin_state, kernel_state in volumes:
            text = []
            error = False
            if admin_state not in {"CLEAN", "ACTIVE"}:
                state = 2
                text.append(f"{volume}: Admin state is {admin_state}(!!)")
                error = True
            if kernel_state not in {"ENABLED", "DISABLED"}:
                state = 2
                text.append(f"{volume}: Kernel state is {kernel_state}(!!)")
                error = True
            if error is False:
                text = ["%s: OK" % volume]
            messages.append(", ".join(text))
        return (state, ", ".join(messages))

    return (2, "Group not found")


def parse_vxvm_objstatus(string_table: StringTable) -> StringTable:
    return string_table


check_info["vxvm_objstatus"] = LegacyCheckDefinition(
    name="vxvm_objstatus",
    parse_function=parse_vxvm_objstatus,
    service_name="VXVM objstatus %s",
    discovery_function=discover_vxvm_objstatus,
    check_function=check_vxvm_objstatus,
)
