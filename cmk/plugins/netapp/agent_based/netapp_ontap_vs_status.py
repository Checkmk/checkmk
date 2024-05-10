#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.netapp import models

Section = Mapping[str, models.SvmModel]

# <<<netapp_ontap_vs_status:sep(0)>>>
# {"name": "svm_ansible_01_jl", "state": "running", "subtype": "sync_source"}
# {"name": "mcc_darz_b_svm02_NFS-mc", "state": "stopped", "subtype": "sync_destination"}


def parse_netapp_ontap_vs_status(string_table: StringTable) -> Section:
    svms: dict[str, models.SvmModel] = {}
    for line in string_table:
        svm = models.SvmModel.model_validate_json(line[0])
        svms[svm.name] = svm

    return svms


agent_section_netapp_ontap_vs_status = AgentSection(
    name="netapp_ontap_vs_status",
    parse_function=parse_netapp_ontap_vs_status,
)


def discover_netapp_ontap_vs_status(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_netapp_ontap_vs_status(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)) or data.state is None:
        return

    state = (
        State.OK
        if (
            data.state == "running"
            or (data.state == "stopped" and data.subtype == "dp_destination")
        )
        else State.CRIT
    )

    yield Result(state=state, summary=f"State: {data.state}")
    if data.subtype is not None:
        yield Result(state=State.OK, summary=f"Subtype: {data.subtype}")


check_plugin_netapp_ontap_vs_status = CheckPlugin(
    name="netapp_ontap_vs_status",
    service_name="SVM Status %s",
    discovery_function=discover_netapp_ontap_vs_status,
    check_function=check_netapp_ontap_vs_status,
)
