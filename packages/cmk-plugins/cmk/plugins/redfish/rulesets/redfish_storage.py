#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""rule for check parameters of storage controllers"""

from cmk.rulesets.v1 import form_specs, Help, rule_specs, Title
from cmk.rulesets.v1.form_specs import validators


def _parameter_valuespec_redfish_storage() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("Redfish Storage Controller"),
        elements={
            "check_type": form_specs.DictElement(
                parameter_form=form_specs.SingleChoice(
                    title=Title("Check type"),
                    help_text=Help(
                        "Specify how the storage controller should be checked:\n\n"
                        " Full: Report detailed controller status including"
                        " RAID levels and device protocols\n\n"
                        " Rollup: Only report overall health state"
                    ),
                    elements=[
                        form_specs.SingleChoiceElement(
                            name="full", title=Title("Full controller status")
                        ),
                        form_specs.SingleChoiceElement(
                            name="rollup", title=Title("Rollup check only")
                        ),
                    ],
                ),
            ),
        },
    )


rule_spec_redfish_storage = rule_specs.CheckParameters(
    name="redfish_storage",
    title=Title("Redfish Storage Controller"),
    topic=rule_specs.Topic.SERVER_HARDWARE,
    condition=rule_specs.HostAndItemCondition(
        item_title=Title("Controller ID"),
        item_form=form_specs.String(custom_validate=(validators.LengthInRange(min_value=1),)),
    ),
    parameter_form=_parameter_valuespec_redfish_storage,
)
