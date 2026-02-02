#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.rulesets.v1 import Help, Label, Title
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
            "status_map": DictElement(
                parameter_form=Dictionary(
                    title=Title("Map uplink status to monitoring state"),
                    elements={
                        "active": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Uplink status "active"'),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                            required=True,
                        ),
                        "ready": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Uplink status "ready"'),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                            required=True,
                        ),
                        "connecting": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Uplink status "connecting"'),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                            required=True,
                        ),
                        "not_connected": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Uplink status "not connected"'),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                            required=True,
                        ),
                        "failed": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Uplink status "failed"'),
                                prefill=DefaultValue(ServiceState.CRIT),
                            ),
                            required=True,
                        ),
                    },
                )
            ),
            "show_traffic": DictElement(
                parameter_form=FixedValue(
                    title=Title("Show bandwidth (use only with cache disabled)"),
                    help_text=Help(
                        "Use only with cache disabled in the Meraki special agent settings. "
                        "The throughput is based on the usage for the last 60 seconds."
                    ),
                    value=True,
                    label=Label("Bandwidth monitoring enabled"),
                )
            ),
        },
    )


rule_spec_cisco_meraki_org_appliance_uplinks = CheckParameters(
    name="cisco_meraki_org_appliance_uplinks",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki appliance uplinks"),
    condition=HostAndItemCondition(item_title=Title("Uplink name")),
)
