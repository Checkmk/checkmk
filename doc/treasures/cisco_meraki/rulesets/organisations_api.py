#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2023-11-18
# File  : cisco_meraki_organisations_api.py (wato plugin)

# 2024-06-29: refactored for CMK 2.3
# 2024-06-30: renamed from cisco_meraki_organisations_api.py in to organisations_api.py
#             moved ruleset from "Networking" to "Applications, Processes & Services"

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "state_api_not_enabled": DictElement(
             parameter_form=ServiceState(
                 title=Title('Monitoring state if API is not enabled'),
                 prefill=DefaultValue(ServiceState.WARN),
             )),

            # params from discovery
            'internal_item_name': DictElement(
                render_only=True,
                parameter_form=String(
                    title=Title('Discovery internal item name')
                )),
            'item_variant': DictElement(
                render_only=True,
                parameter_form=String(
                    title=Title('Discovery item variant')
                )),
        },
    )


rule_spec_cisco_meraki_organisations_api = CheckParameters(
    name="cisco_meraki_organisations_api",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki Organisation API"),
    condition=HostAndItemCondition(item_title=Title('Organization')),
)

