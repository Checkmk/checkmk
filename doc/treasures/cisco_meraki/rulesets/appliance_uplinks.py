#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2023-11-05
# File  : cisco_meraki_org_appliance_uplinks.py (WATO)

# 2024-06-29: refactored for CMK 2.3
# 2024-06-30: renamed from cisco_meraki_org_appliance_uplinks.py in to appliance_uplinks.py

from cmk.rulesets.v1 import Label, Title, Help
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            'status_map': DictElement(
                parameter_form=Dictionary(
                    title=Title('Map uplink status to monitoring state'),
                    elements={
                        "active": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Uplink status "active"'),
                                prefill=DefaultValue(ServiceState.OK)
                            )),
                        "ready": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Uplink status "ready"'),
                                prefill=DefaultValue(ServiceState.WARN),
                            )),
                        "not_connected": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Uplink status "not connected"'),
                                prefill=DefaultValue(ServiceState.CRIT),
                            )),
                        "failed": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Uplink status "failed"'),
                                prefill=DefaultValue(ServiceState.CRIT),
                            )),
                    },
                )),
            'show_traffic': DictElement(
                parameter_form=FixedValue(
                    title=Title('Show bandwidth (use only with cache disabled)'),
                    help_text=Help(
                        'Use only with cache disabled in the Meraki special agent settings. '
                        'The throughput is based on the usage for the last 60 seconds.'
                    ),
                    value=True,
                    label=Label("Bandwidth monitoring enabled")
                ))
        },
    )


rule_spec_cisco_meraki_org_appliance_uplinks = CheckParameters(
    name="cisco_meraki_org_appliance_uplinks",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki Appliance uplinks"),
    condition=HostAndItemCondition(item_title=Title('Uplink name')),
)
