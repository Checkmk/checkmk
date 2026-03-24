#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""rule for naming at discovery of volumes"""

from cmk.rulesets.v1 import form_specs, Help, rule_specs, Title


def _form_discovery_redfish_volumes() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("Redfish Volume discovery"),
        elements={
            "item": form_specs.DictElement(
                parameter_form=form_specs.SingleChoice(
                    title=Title("Discovery settings for volumes"),
                    help_text=Help(
                        "Specify how to name volumes during discovery:\n\n"
                        " Classic: Use the volume ID\n\n"
                        " Controller ID: Use a structured format from the OData path"
                        " (e.g., '0:1:4' for system:storage:volume)"
                    ),
                    elements=[
                        form_specs.SingleChoiceElement(name="classic", title=Title("Classic")),
                        form_specs.SingleChoiceElement(name="ctrlid", title=Title("Controller ID")),
                    ],
                ),
            ),
        },
    )


rule_spec_discovery_redfish_volumes = rule_specs.DiscoveryParameters(
    title=Title("Redfish Volume discovery"),
    topic=rule_specs.Topic.SERVER_HARDWARE,
    name="discovery_redfish_volumes",
    parameter_form=_form_discovery_redfish_volumes,
)
