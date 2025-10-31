#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    State,
)
from cmk.plugins.vsphere.lib import esx_vsphere


def discovery_name(section: esx_vsphere.SectionESXVm) -> DiscoveryResult:
    if section.name is not None:
        yield Service()


def check_name(section: esx_vsphere.SectionESXVm) -> CheckResult:
    if section.name is None:
        raise IgnoreResultsError("No information about name")

    yield Result(state=State.OK, summary=section.name)


check_plugin_esx_vsphere_vm_name = CheckPlugin(
    name="esx_vsphere_vm_name",
    sections=["esx_vsphere_vm"],
    service_name="ESX Name",
    discovery_function=discovery_name,
    check_function=check_name,
)
