#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import IgnoreResultsError, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils import esx_vsphere


def discovery_name(section: esx_vsphere.SectionVM) -> DiscoveryResult:
    if section is None:
        return
    if section.name is not None:
        yield Service()


def check_name(section: esx_vsphere.SectionVM) -> CheckResult:
    if section is None:
        raise IgnoreResultsError("No VM information currently available")

    if section.name is None:
        raise IgnoreResultsError("No information about name")

    yield Result(state=State.OK, summary=section.name)


register.check_plugin(
    name="esx_vsphere_vm_name",
    sections=["esx_vsphere_vm"],
    service_name="ESX Name",
    discovery_function=discovery_name,
    check_function=check_name,
)
