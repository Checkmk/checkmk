#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import NewType

from ..agent_based_api.v1.type_defs import StringTable

Version = NewType("Version", str)


class Error:
    pass


@dataclasses.dataclass
class Session:
    active: int = 0
    inactive: int = 0


@dataclasses.dataclass
class Section:
    version: None | Version = None
    state: str | Error | None = None
    licensing_grace_state: str | None = None
    licensing_server_state: str | None = None
    session: Session | None = None
    desktop_count: int | Error | None = None
    active_site_services: str | None = None


def parse_citrix_controller(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    section = Section()
    session = Session()
    # piggy back data might deliver double data
    detected_states = []
    for line in string_table:
        if line[0] == "ControllerVersion" and len(line) > 1:
            section.version = Version(line[1])
        if line[0] == "ControllerState":
            section.state = line[1] if len(line) > 1 else Error()
        if (
            line[0].lower() == "licensinggracestate"
            and line[0] not in detected_states
            and len(line) > 1
        ):
            detected_states.append(line[0])
            section.licensing_grace_state = line[1]
        if (
            line[0].lower() == "licensingserverstate"
            and line[0] not in detected_states
            and len(line) > 1
        ):
            detected_states.append(line[0])
            section.licensing_server_state = line[1]
        if line[0] == "TotalFarmActiveSessions":
            session.active = int(line[1])
            section.session = session
        elif line[0] == "TotalFarmInactiveSessions":
            session.inactive = int(line[1])
            section.session = session
        if line[0] == "DesktopsRegistered":
            try:
                section.desktop_count = int(line[1])
            except (IndexError, ValueError):
                section.desktop_count = Error()
        if line[0] == "ActiveSiteServices":
            section.active_site_services = " ".join(line[1:])
    return section
