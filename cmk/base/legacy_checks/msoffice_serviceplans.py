#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Example output:
# <<<msoffice_serviceplans>>>
# mggraph:VISIOCLIENT ONEDRIVE_BASIC Success
# mggraph:VISIOCLIENT VISIOONLINE Success
# mggraph:VISIOCLIENT EXCHANGE_S_FOUNDATION Success
# mggraph:VISIOCLIENT VISIO_CLIENT_SUBSCRIPTION Success
# mggraph:POWER_BI_PRO EXCHANGE_S_FOUNDATION Success
# mggraph:POWER_BI_PRO BI_AZURE_P2 Success
# mggraph:WINDOWS_STORE EXCHANGE_S_FOUNDATION Success
# mggraph:WINDOWS_STORE WINDOWS_STORE PendingActivation


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_msoffice_serviceplans(info):
    for line in info:
        if len(line) >= 1 and "Microsoft.Graph module is not installed" in " ".join(line):
            yield "_error", {}
            return
        yield line[0], {}


def check_msoffice_serviceplans(item, params, info):
    success = 0
    pending = 0
    pending_list = []
    warn, crit = params.get("levels", (None, None))
    for line in info:
        if len(line) >= 1 and "Microsoft.Graph module is not installed" in " ".join(line):
            yield (
                2,
                "MS Office agent plugin requires installation of the Powershell Module Microsoft.Graph for all users, see werk #18609",
            )
            return

        bundle, plan, status = line[0], " ".join(line[1:-1]), line[-1]
        if bundle == item:
            if status == "Success":
                success += 1
            elif status == "PendingActivation":
                pending += 1
                pending_list.append(plan)
    state = 0
    infotext = "Success: %d, Pending: %d" % (success, pending)
    if crit and pending >= crit:
        state = 2
    elif warn and pending >= warn:
        state = 1
    if state:
        infotext += " (warn/crit at %d/%d)" % (warn, crit)
    yield state, infotext
    if pending_list:
        yield 0, "Pending Services: %s" % ", ".join(pending_list)


def parse_msoffice_serviceplans(string_table: StringTable) -> StringTable:
    return string_table


check_info["msoffice_serviceplans"] = LegacyCheckDefinition(
    name="msoffice_serviceplans",
    parse_function=parse_msoffice_serviceplans,
    service_name="MS Office Serviceplans %s",
    discovery_function=discover_msoffice_serviceplans,
    check_function=check_msoffice_serviceplans,
    check_ruleset_name="msoffice_serviceplans",
)
