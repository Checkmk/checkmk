#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    MultipleChoice,
    MultipleChoiceElement,
    ServiceState,
    String,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    DiscoveryParameters,
    HostAndItemCondition,
    Topic,
)


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "state_admin_change": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state if admin state changed"),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
            "state_disabled": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state if port was disabled"),
                    prefill=DefaultValue(ServiceState.OK),
                )
            ),
            "state_not_connected": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state if port is not connected"),
                    prefill=DefaultValue(ServiceState.OK),
                )
            ),
            "state_not_full_duplex": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state if port is not full duplex"),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
            "state_op_change": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state if operational state changed"),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
            "state_speed_change": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state if speed changed"),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
            # Discovered parameters
            "admin_state": DictElement(
                render_only=True,
                parameter_form=String(
                    title=Title("Discovered admin state"),
                ),
            ),
            "operational_state": DictElement(
                render_only=True,
                parameter_form=String(
                    title=Title("Discovered operational state"),
                ),
            ),
            "speed": DictElement(
                render_only=True,
                parameter_form=String(
                    title=Title("Discovered speed"),
                ),
            ),
        },
    )


rule_spec_cisco_meraki_switch_ports_statuses = CheckParameters(
    name="cisco_meraki_switch_ports_statuses",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki switch port statuses"),
    condition=HostAndItemCondition(item_title=Title("Port ID")),
)


def _discovery_parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "operational_port_states": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Match port states"),
                    elements=[
                        MultipleChoiceElement(
                            title=Title("1 - up"),
                            name="up",
                        ),
                        MultipleChoiceElement(
                            title=Title("2 - down"),
                            name="down",
                        ),
                    ],
                    help_text=Help(
                        "Apply this rule only to interfaces whose port state is listed below."
                    ),
                    prefill=DefaultValue(["up", "down"]),
                )
            ),
            "admin_port_states": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Match admin states"),
                    elements=[
                        MultipleChoiceElement(
                            title=Title("1 - up"),
                            name="up",
                        ),
                        MultipleChoiceElement(
                            title=Title("2 - down"),
                            name="down",
                        ),
                    ],
                    help_text=Help(
                        "Apply this rule only to interfaces whose admin state is listed below"
                    ),
                    prefill=DefaultValue(["up", "down"]),
                )
            ),
        },
    )


rule_spec_cisco_meraki_switch_ports_statuses_discovery = DiscoveryParameters(
    name="discovery_cisco_meraki_switch_ports_statuses",
    topic=Topic.NETWORKING,
    parameter_form=_discovery_parameter_form,
    title=Title("Cisco Meraki switch port statuses"),
)
