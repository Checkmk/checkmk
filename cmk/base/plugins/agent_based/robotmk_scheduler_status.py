#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.utils import robotmk_api


def discover_scheduler_status(section: robotmk_api.Section) -> DiscoveryResult:
    if section.config or section.config_reading_error:
        yield Service()


def check_scheduler_status(section: robotmk_api.Section) -> CheckResult:
    if not (section.config or section.config_reading_error):
        return

    # TODO: Determine the conditions for the status
    yield Result(state=State.OK, summary="The Scheduler status is OK")


register.check_plugin(
    name="robotmk_scheduler_status",
    sections=["robotmk_v2"],
    service_name="Robotmk Scheduler Status",
    discovery_function=discover_scheduler_status,
    check_function=check_scheduler_status,
)
