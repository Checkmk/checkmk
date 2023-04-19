#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import IgnoreResultsError, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils import esx_vsphere


def discovery_datastores(section: esx_vsphere.SectionVM) -> DiscoveryResult:
    if section is None:
        return

    if section.datastores is not None:
        yield Service()


def check_datastores(section: esx_vsphere.SectionVM) -> CheckResult:
    if section is None:
        raise IgnoreResultsError("No VM information currently available")

    if section.datastores is None:
        yield Result(state=State.UNKNOWN, summary="Datastore information is missing")
        return

    output = []
    for datastore in section.datastores:
        output.append(
            f"Stored on {datastore.name} ({render.bytes(datastore.capacity)}/"
            f"{datastore.free_space / datastore.capacity * 100 if datastore.capacity else 0.0:.1f}% free)"
        )
    yield Result(state=State.OK, summary=", ".join(output))


register.check_plugin(
    name="esx_vsphere_vm_datastores",
    sections=["esx_vsphere_vm"],
    service_name="ESX Datastores",
    discovery_function=discovery_datastores,
    check_function=check_datastores,
)
