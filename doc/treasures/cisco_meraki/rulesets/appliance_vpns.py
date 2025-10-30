#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2023-11-05
# File  : cisco_meraki_org_appliance_vpns.py (WATO)

# 2024-06-29: refactored for CMK 2.3
# 2024-06-30: renamed from cisco_meraki_org_appliance_vpns.py in to appliance_vpns.py

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
            'status_not_reachable': DictElement(
                parameter_form=ServiceState(
                    title=Title('Monitoring state if the VPN peer is not reachable'),
                    prefill=DefaultValue(ServiceState.WARN),
                )),
        }
    )


rule_spec_cisco_meraki_org_appliance_vpns = CheckParameters(
    name="cisco_meraki_org_appliance_vpns",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki Appliance VPNs"),
    condition=HostAndItemCondition(item_title=Title('VPN peer')),
)
