#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""rule for naming at discovery of outlets"""

from cmk.rulesets.v1 import form_specs, Help, rule_specs, Title


def _form_discovery_redfish_outlets() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("Redfish outlet discovery"),
        elements={
            "naming": form_specs.DictElement(
                parameter_form=form_specs.SingleChoice(
                    title=Title("Naming for outlets at discovery"),
                    help_text=Help(
                        "Specify how to name the outlets during discovery:\n\n"
                        " Port ID: Use the ID of the port as name\n\n"
                        " User Label: Add the user label of the ports name, in addition to the ID: 'ID-UserLabel'\n\n"
                        " Zero padded port ID: Use the zero padded port ID (to the length of the highest port ID)"
                    ),
                    elements=[
                        form_specs.SingleChoiceElement(name="index", title=Title("Port ID")),
                        form_specs.SingleChoiceElement(name="label", title=Title("User Label")),
                        form_specs.SingleChoiceElement(
                            name="fill", title=Title("Zero padded port ID")
                        ),
                    ],
                ),
            ),
        },
    )


rule_spec_discovery_redfish_outlets = rule_specs.DiscoveryParameters(
    title=Title("Redfish outlet discovery"),
    topic=rule_specs.Topic.SERVER_HARDWARE,
    name="discovery_redfish_outlets",
    parameter_form=_form_discovery_redfish_outlets,
)
