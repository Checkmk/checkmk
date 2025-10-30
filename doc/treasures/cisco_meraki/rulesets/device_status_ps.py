#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2024-06-30
# File  : cisco_meraki_org_device_status_ps.py (WATO)

# 2024-06-30: created to shadow built-in file -> move rule from "Applications, Processes & Services" to "Hardware, BIOS"
# 2025-03-30: moved to ruleset APIv1

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
