#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.utils import robotmk_api  # Should be replaced by external package


def discover_scheduler_status(section: robotmk_api.ConfigFileContent | None) -> DiscoveryResult:
    if section:
        yield Service(item="Robotmk Scheduler Status")


def check_scheduler_status(item: str, section: robotmk_api.ConfigFileContent | None) -> CheckResult:
    if not section:
        return

    # TODO: Determine the conditions for the status
    yield Result(state=State.OK, summary="The Scheduler status is OK")


register.check_plugin(
    name="robotmk_scheduler_status",
    sections=["robotmk_v2"],
    service_name="%s",
    discovery_function=discover_scheduler_status,
    check_function=check_scheduler_status,
)
