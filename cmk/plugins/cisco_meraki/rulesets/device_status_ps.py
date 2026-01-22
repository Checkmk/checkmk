#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
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


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "state_not_powering": DictElement(
                parameter_form=ServiceState(
                    title=Title('Monitoring state if power supply is not "powering"'),
                    prefill=DefaultValue(1),
                )
            ),
        }
    )


rule_spec_cisco_meraki_org_device_status_ps = CheckParameters(
    name="cisco_meraki_org_device_status_ps",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki power supply"),
    condition=HostAndItemCondition(item_title=Title("Slot number")),
)
