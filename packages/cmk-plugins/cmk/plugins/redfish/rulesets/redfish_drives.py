#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""rule for naming at discovery of physical drives"""

from cmk.rulesets.v1 import form_specs, Help, rule_specs, Title


def _form_discovery_redfish_drives() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("Redfish Physical Drive discovery"),
        elements={
            "item": form_specs.DictElement(
                parameter_form=form_specs.SingleChoice(
                    title=Title("Discovery settings for physical drives"),
                    help_text=Help(
                        "Specify how to name drives during discovery:\n\n"
                        " Classic: Use the drive ID and name (e.g., '0-1.2TB 12G SAS HDD')\n\n"
                        " Controller ID: Use a structured format from the OData path"
                        " (e.g., '0:1:4' for system:storage:drive)"
                    ),
                    elements=[
                        form_specs.SingleChoiceElement(name="classic", title=Title("Classic")),
                        form_specs.SingleChoiceElement(name="ctrlid", title=Title("Controller ID")),
                    ],
                ),
            ),
        },
    )


rule_spec_discovery_redfish_drives = rule_specs.DiscoveryParameters(
    title=Title("Redfish Physical Drive discovery"),
    topic=rule_specs.Topic.SERVER_HARDWARE,
    name="discovery_redfish_drives",
    parameter_form=_form_discovery_redfish_drives,
)
