#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""rule for naming at discovery of outlets"""
# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# License: GNU General Public License v2

from cmk.rulesets.v1 import form_specs, Help, rule_specs, Title


def _form_discovery_redfish_outlets() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("Redfish outlet discovery"),
        elements={
            "naming": form_specs.DictElement(
                parameter_form=form_specs.SingleChoice(
                    title=Title("Naming for outlets at discovery"),
                    help_text=Help("Specify how to name the outlets at discovered"),
                    elements=[
                        form_specs.SingleChoiceElement(
                            name="index", title=Title("Port Index")
                        ),
                        form_specs.SingleChoiceElement(
                            name="label", title=Title("User Label")
                        ),
                        form_specs.SingleChoiceElement(
                            name="fill", title=Title("Port Index with fill")
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
