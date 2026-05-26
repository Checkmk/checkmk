#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def discover_msoffice_serviceplans(section: StringTable) -> DiscoveryResult:
    for line in section:
        if len(line) >= 1 and "Microsoft.Graph module is not installed" in " ".join(line):
            yield Service(item="_error")
            return
        yield Service(item=line[0])


def check_msoffice_serviceplans(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    success = 0
    pending = 0
    pending_list = []
    warn, crit = params.get("levels", (None, None))
    for line in section:
        if len(line) >= 1 and "Microsoft.Graph module is not installed" in " ".join(line):
            yield Result(
                state=State.CRIT,
                summary="MS Office agent plugin requires installation of the Powershell Module Microsoft.Graph for all users, see werk #18609",
            )
            return

        bundle, plan, status = line[0], " ".join(line[1:-1]), line[-1]
        if bundle == item:
            if status == "Success":
                success += 1
            elif status == "PendingActivation":
                pending += 1
                pending_list.append(plan)
    state = State.OK
    infotext = f"Success: {success}, Pending: {pending}"
    if crit and pending >= crit:
        state = State.CRIT
    elif warn and pending >= warn:
        state = State.WARN
    if state is not State.OK:
        infotext += f" (warn/crit at {warn}/{crit})"
    yield Result(state=state, summary=infotext)
    if pending_list:
        yield Result(state=State.OK, summary=f"Pending Services: {', '.join(pending_list)}")


def parse_msoffice_serviceplans(string_table: StringTable) -> StringTable:
    return string_table


agent_section_msoffice_serviceplans = AgentSection(
    name="msoffice_serviceplans",
    parse_function=parse_msoffice_serviceplans,
)


check_plugin_msoffice_serviceplans = CheckPlugin(
    name="msoffice_serviceplans",
    service_name="MS Office Serviceplans %s",
    discovery_function=discover_msoffice_serviceplans,
    check_function=check_msoffice_serviceplans,
    check_ruleset_name="msoffice_serviceplans",
    check_default_parameters={},
)
