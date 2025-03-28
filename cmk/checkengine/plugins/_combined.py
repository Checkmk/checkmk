#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Self

from cmk.utils.sectionname import SectionName

from ._check import CheckPlugin, CheckPluginName
from ._inventory import InventoryPlugin, InventoryPluginName
from ._sections import AgentSectionPlugin, SNMPSectionPlugin


@dataclass(frozen=True, kw_only=True)
class AgentBasedPlugins:
    agent_sections: Mapping[SectionName, AgentSectionPlugin]
    snmp_sections: Mapping[SectionName, SNMPSectionPlugin]
    check_plugins: Mapping[CheckPluginName, CheckPlugin]
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin]
    errors: Sequence[str]

    @classmethod
    def empty(cls) -> Self:
        return cls(
            agent_sections={},
            snmp_sections={},
            check_plugins={},
            inventory_plugins={},
            errors=(),
        )
