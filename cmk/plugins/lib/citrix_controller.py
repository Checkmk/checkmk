#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import NewType

from cmk.agent_based.v1.type_defs import StringTable

Version = NewType("Version", str)


class Error:
    pass


@dataclasses.dataclass
class Session:
    active: int = 0
    inactive: int = 0


@dataclasses.dataclass
class Section:
    version: Version | None = None
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
    for line in string_table:
        match line:
            case ["ControllerVersion", version, *_]:
                section.version = Version(version)
            case ["ControllerState", state, *_]:
                section.state = state
            case ["ControllerState", *_]:
                section.state = Error()
            # piggy back data might deliver double data
            case ["LicensingGraceState", grace, *_] if section.licensing_grace_state is None:
                section.licensing_grace_state = grace
            case ["LicensingServerState", server, *_] if section.licensing_server_state is None:
                section.licensing_server_state = server
            case ["TotalFarmActiveSessions", active, *_]:
                session.active = int(active)
                section.session = session
            case ["TotalFarmInactiveSessions", inactive, *_]:
                session.inactive = int(inactive)
                section.session = session
            case ["DesktopsRegistered", value, *_] if value.isdigit():
                section.desktop_count = int(value)
            case ["DesktopsRegistered", *_]:
                section.desktop_count = Error()
            case ["ActiveSiteServices", *services]:
                section.active_site_services = " ".join(services)
    return section
