#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api import v1
from cmk.base.plugins.agent_based.utils.citrix_controller import Error, Section


def discovery_citrix_controller(section: Section) -> v1.type_defs.DiscoveryResult:
    if section.state is not None:
        yield v1.Service()


def check_citrix_controller(section: Section) -> v1.type_defs.CheckResult:
    match section.state:
        case None:
            return
        case Error():
            yield v1.Result(state=v1.State.UNKNOWN, summary="unknown")
        case "Active":
            yield v1.Result(state=v1.State.OK, summary=section.state)
        case _:
            yield v1.Result(state=v1.State.CRIT, summary=section.state)


v1.register.check_plugin(
    name="citrix_controller",
    discovery_function=discovery_citrix_controller,
    check_function=check_citrix_controller,
    service_name="Citrix Controller State",
)
