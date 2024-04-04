#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import form_specs, Help, rule_specs, Title


def _form_discovery_netapp_api_ports_ignored() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("Netapp port discovery"),
        elements={
            "ignored_ports": form_specs.DictElement(
                parameter_form=form_specs.MultipleChoice(
                    title=Title("Ignore port types during discovery"),
                    help_text=Help("Specify which port types should not be discovered"),
                    elements=[
                        form_specs.MultipleChoiceElement(name="physical", title=Title("Physical")),
                        form_specs.MultipleChoiceElement(name="vlan", title=Title("Vlan")),
                        form_specs.MultipleChoiceElement(name="trunk", title=Title("Trunk")),
                    ],
                ),
            ),
        },
    )


rule_spec_discovery_netapp_api_ports_ignored = rule_specs.DiscoveryParameters(
    title=Title("Netapp port discovery"),
    topic=rule_specs.Topic.GENERAL,
    name="discovery_netapp_api_ports_ignored",
    parameter_form=_form_discovery_netapp_api_ports_ignored,
)
