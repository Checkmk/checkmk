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
            "state_api_not_enabled": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state if API is not enabled"),
                    prefill=DefaultValue(2),
                )
            ),
        }
    )


rule_spec_cisco_meraki_org_device_status_ps = CheckParameters(
    name="cisco_meraki_org_api_response_codes",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki organization API"),
    condition=HostAndItemCondition(item_title=Title("Organization")),
)
