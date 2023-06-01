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
class Section:
    version: None | Version = None
    state: str | Error | None = None


def parse_citrix_controller(string_table: StringTable) -> Section:
    section = Section()
    for line in string_table:
        if line[0] == "ControllerVersion" and len(line) > 1:
            section.version = Version(line[1])
        if line[0] == "ControllerState":
            section.state = line[1] if len(line) > 1 else Error()
    return section
