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


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "state_if_not_enabled": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state if SSID is not enabled"),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
        },
    )


rule_spec_cisco_meraki_wireless_device_status_ssids = CheckParameters(
    name="cisco_meraki_org_wireless_device_statuses_ssids",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki wireless device statuses"),
    condition=HostAndItemCondition(item_title=Title("SSID")),
)
