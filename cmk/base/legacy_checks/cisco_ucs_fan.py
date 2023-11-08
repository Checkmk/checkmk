#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping
from typing import Any

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cisco_ucs import DETECT
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.cisco_ucs import Operability


def inventory_cisco_ucs_fan(section: Mapping[str, Operability]) -> Iterator[Any]:
    yield from ((name, None) for name in section.keys())


def check_cisco_ucs_fan(
    item: str, _no_params: object, section: Mapping[str, Operability]
) -> tuple[int, str] | None:
    if not (operability := section.get(item)):
        return None

    return operability.monitoring_state().value, f"Status: {operability.name}"


check_info["cisco_ucs_fan"] = LegacyCheckDefinition(
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.15.12.1",
        oids=["2", "10"],
    ),
    service_name="Fan %s",
    discovery_function=inventory_cisco_ucs_fan,
    check_function=check_cisco_ucs_fan,
)
