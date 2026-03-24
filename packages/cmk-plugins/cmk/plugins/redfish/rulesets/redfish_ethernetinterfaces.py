#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""rules for discovery and check of ethernet interfaces"""

from cmk.rulesets.v1 import form_specs, Help, rule_specs, Title
from cmk.rulesets.v1.form_specs import validators


def _form_discovery_redfish_ethernetinterfaces() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("Redfish physical port discovery"),
        elements={
            "state": form_specs.DictElement(
                parameter_form=form_specs.SingleChoice(
                    title=Title("Discovery settings for physical ports"),
                    help_text=Help("Specify if port state UP, DOWN or booth should be discovered"),
                    elements=[
                        form_specs.SingleChoiceElement(name="up", title=Title("Up only")),
                        form_specs.SingleChoiceElement(name="down", title=Title("Down only")),
                        form_specs.SingleChoiceElement(name="updown", title=Title("Up & Down")),
                    ],
                ),
            ),
        },
    )


rule_spec_discovery_redfish_ethernetinterfaces = rule_specs.DiscoveryParameters(
    title=Title("Redfish Ethernet Interface discovery"),
    topic=rule_specs.Topic.SERVER_HARDWARE,
    name="discovery_redfish_ethernetinterfaces",
    parameter_form=_form_discovery_redfish_ethernetinterfaces,
)


def _form_redfish_ethernetinterfaces() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("Redfish Ethernet Interface"),
        elements={
            "state_if_link_status_changed": form_specs.DictElement(
                parameter_form=form_specs.ServiceState(
                    title=Title("State if link status changed"),
                    prefill=form_specs.DefaultValue(2),
                ),
            ),
            "state_if_link_speed_changed": form_specs.DictElement(
                parameter_form=form_specs.ServiceState(
                    title=Title("State if link speed changed"),
                    prefill=form_specs.DefaultValue(1),
                ),
            ),
        },
        ignored_elements=("discover_speed", "discover_link_status"),
    )


rule_spec_redfish_ethernetinterfaces = rule_specs.CheckParameters(
    name="check_redfish_ethernetinterfaces",
    title=Title("Redfish Ethernet Interface"),
    topic=rule_specs.Topic.SERVER_HARDWARE,
    condition=rule_specs.HostAndItemCondition(
        item_title=Title("Physical port"),
        item_form=form_specs.String(custom_validate=(validators.LengthInRange(min_value=1),)),
    ),
    parameter_form=_form_redfish_ethernetinterfaces,
)
