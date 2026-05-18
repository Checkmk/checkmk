#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
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
            "differing_service_state": DictElement(
                required=True,
                parameter_form=ServiceState(
                    title=Title("Service state for differing VM/LXC states"),
                    help_text=Help(
                        "The state of the Proxmox VE HA Manager Watcher service will be set to this value "
                        "if the current state of a VM/LXC differs from its requested state"
                    ),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        },
    )


rule_spec_proxmox_ve_ha_manager_status = CheckParameters(
    name="proxmox_ve_ha_manager_status",
    topic=Topic.CLOUD,
    parameter_form=_parameter_valuespec_proxmox_ve_ha_manager_status,
    title=Title("Proxmox VE HA Manager Watcher"),
    condition=HostAndItemCondition(Title("Node")),
)
