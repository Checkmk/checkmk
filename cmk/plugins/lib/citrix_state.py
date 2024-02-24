#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1.type_defs import StringTable

Section = Mapping[str, Any]


def parse_citrix_state(string_table: StringTable) -> Section:
    section: dict[str, Any] = {
        "instance": {},
    }
    for line in string_table:
        if line[0] == "Controller":
            section["controller"] = " ".join(line[1:])
        elif line[0] == "HostingServer":
            section["hosting_server"] = " ".join(line[1:])
        elif line[0] in [
            "FaultState",
            "MaintenanceMode",
            "PowerState",
            "RegistrationState",
            "VMToolsState",
            "AgentVersion",
            "Catalog",
            "DesktopGroupName",
        ]:
            section["instance"][line[0]] = " ".join(line[1:])

    return section
