#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils import netapp_ontap_models as models

Section = Mapping[str, models.SvmModel]

# <<<netapp_ontap_vs_status:sep(0)>>>
# {"name": "svm_ansible_01_jl", "state": "running", "subtype": "sync_source"}
# {"name": "mcc_darz_b_svm02_NFS-mc", "state": "stopped", "subtype": "sync_destination"}


def parse_netapp_ontap_vs_status(string_table: StringTable) -> Section:
    svms: dict[str, models.SvmModel] = {}
    for line in string_table:
        svm = models.SvmModel(**json.loads(line[0]))
        svms[svm.name] = svm

    return svms


register.agent_section(
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


register.check_plugin(
    name="netapp_ontap_vs_status",
    service_name="SVM Status %s",
    discovery_function=discover_netapp_ontap_vs_status,
    check_function=check_netapp_ontap_vs_status,
)
