#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2023-11-04
# File  : cisco_meraki_org_device_status_ps.py (WATO)

# 2023-12-03: moved to CMK 2.3 API v2
# 2012-12-17: splitt device status and power supply


from cmk.rulesets.v1 import (
    CheckParameterRuleSpecWithItem,
    DictElement,
    Dictionary,
    disallow_empty,
    Localizable,
    MonitoringState,
    State,
    TextInput,
    Topic,
)


def _parameter_form_cisco_meraki_device_status_ps():
    return Dictionary(
        # title=_("Cisco Meraki Powersupply status"),
        # optional_keys=True,
        elements={
            "state_not_powering": DictElement(
                parameter_form=MonitoringState(
                    title=Localizable('Monitoring state if power supply is not "powering"'),
                    prefill_value=State.WARN,
                )
            )
        }
    )


rule_spec_cisco_meraki_device_status_ps = CheckParameterRuleSpecWithItem(
    name="cisco_meraki_org_device_status_ps",
    topic=Topic.APPLICATIONS,  # missing HARDWARE
    # group=RulespecGroupCheckParametersHardware,
    item_form=TextInput(title=Localizable("The Slot number"), custom_validate=disallow_empty()),
    parameter_form=_parameter_form_cisco_meraki_device_status_ps,
    title=Localizable("Cisco Meraki Power supply"),
)
