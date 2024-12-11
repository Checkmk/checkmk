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
