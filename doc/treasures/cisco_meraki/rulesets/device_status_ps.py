#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

#
# Cisco Meraki Power Supply -> now built-in in cmk 2.3
#
def _parameter_from_cisco_meraki_device_status_ps():
    return Dictionary(
        elements={
            "state_not_powering": DictElement(
                parameter_form=ServiceState(
                    title=Title('Monitoring state if power supply is not "powering"'),
                    prefill=DefaultValue(1),
                )),
        }
    )


rule_spec_cisco_meraki_device_status_ps=CheckParameters(
    title=Title("Cisco Meraki Power supply"),
    name="cisco_meraki_device_status_ps",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_from_cisco_meraki_device_status_ps,
    condition=HostAndItemCondition(item_title=Title("Slot number")),
)
