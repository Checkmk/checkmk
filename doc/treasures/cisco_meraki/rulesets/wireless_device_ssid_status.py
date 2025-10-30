#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2024-02-02
# File  : cisco_meraki_org_wireless_status.py (WATO)

# 2024-06-29: refactored for CMK 2.3
# 2024-06-30 renamed from cisco_meraki_org_wireless_device_status.py in to wireless_device_ssid_status.py
#            added SSI to the title

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
            'state_if_not_enabled': DictElement(
                parameter_form=ServiceState(
                    title=Title('Monitoring state if SSID is "not enabled"'),
                    prefill=DefaultValue(ServiceState.WARN),
                )),
        },
    )


rule_spec_cisco_meraki_wireless_device_status = CheckParameters(
    name="cisco_meraki_wireless_device_status",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki Wireless device SSID"),
    condition=HostAndItemCondition(item_title=Title("SSID")),
)
