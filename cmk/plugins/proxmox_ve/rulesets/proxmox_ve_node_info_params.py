#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_rulespec_proxmox_ve_node_info():
    return Dictionary(
        elements={
            "required_node_status": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Node Status (off: ignore node status)"),
                    label=Label("Warn if node status value is not"),
                    prefill=DefaultValue("online"),
                    migrate=lambda v: "" if v is None else str(v),
                ),
            ),
            "required_subscription_status": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Subscription Status (off: ignore subscription status)"),
                    label=Label("Warn if subscription status value is not"),
                    prefill=DefaultValue("Active"),
                    migrate=lambda v: "" if v is None else str(v),
                ),
            ),
        }
    )


rule_spec_proxmox_ve_node_info = CheckParameters(
    name="proxmox_ve_node_info",
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_rulespec_proxmox_ve_node_info,
    title=Title("Proxmox VE Node Info"),
    condition=HostCondition(),
)
