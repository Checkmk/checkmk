#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from typing import Any

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import State
from cmk.base.plugins.agent_based.cisco_ucs_mem import MemoryModule
from cmk.base.plugins.agent_based.utils.cisco_ucs import Presence


def inventory_cisco_ucs_mem(section: Mapping[str, MemoryModule]) -> Iterator[Any]:
    yield from (
        (name, None)
        for name, memory_module in section.items()
        if memory_module.presence is not Presence.missing
    )


def check_cisco_ucs_mem(
    item: str, _no_params: object, section: Mapping[str, MemoryModule]
) -> Iterator[Any]:
    if not (memory_module := section.get(item)):
        return

    yield memory_module.operability.monitoring_state().value, f"Status: {memory_module.operability.name}"
    yield memory_module.presence.monitoring_state().value, f"Presence: {memory_module.presence.name}"
    yield State.OK.value, f"Type: {memory_module.memtype.name}"
    yield State.OK.value, f"Size: {memory_module.capacity} MB, SN: {memory_module.serial}"


check_info["cisco_ucs_mem"] = LegacyCheckDefinition(
    service_name="Memory %s",
    discovery_function=inventory_cisco_ucs_mem,
    check_function=check_cisco_ucs_mem,
)
