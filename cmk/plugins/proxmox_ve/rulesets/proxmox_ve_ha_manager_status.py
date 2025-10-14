#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

# mypy: disable-error-code="no-untyped-def"


def _parameter_valuespec_proxmox_ve_ha_manager_status():
    return Dictionary(
        elements={
            "ignored_vms_state": DictElement(
                required=True,
                parameter_form=ServiceState(
                    title=Title("Service state for Ignored VMs"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "stopped_vms_state": DictElement(
                required=True,
                parameter_form=ServiceState(
                    title=Title("Service state for Stopped VMs"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
        }
    )


rule_spec_proxmox_ve_ha_manager_status = CheckParameters(
    name="proxmox_ve_ha_manager_status",
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_valuespec_proxmox_ve_ha_manager_status,
    title=Title("Proxmox VE HA Manager Watcher"),
    condition=HostAndItemCondition(Title("Node")),
)
