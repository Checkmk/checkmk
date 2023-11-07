#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import (
    CheckParameterRuleSpecWithItem,
    DictElement,
    Dictionary,
    DropdownChoice,
    DropdownChoiceElement,
    Localizable,
    RuleSpecSubGroup,
    TextInput,
)


def _parameter_valuespec_prism_protection_domains():
    return Dictionary(
        elements={
            "sync_state": DictElement(
                spec=DropdownChoice(
                    title=Localizable("Target sync state"),
                    help_text=Localizable(
                        "Configure the target state of the protection domain sync state."
                    ),
                    elements=[
                        DropdownChoiceElement(
                            choice="Enabled", display=Localizable("Sync enabled")
                        ),
                        DropdownChoiceElement(
                            choice="Disabled", display=Localizable("Sync disabled")
                        ),
                        DropdownChoiceElement(
                            choice="Synchronizing", display=Localizable("Syncing")
                        ),
                    ],
                    default_element="Disabled",
                )
            )
        },
    )


rulespec_prims_protection_domains = CheckParameterRuleSpecWithItem(
    name="prism_protection_domains",
    title=Localizable("Nutanix Prism MetroAvail Sync State"),
    group=RuleSpecSubGroup.CHECK_PARAMETERS_VIRTUALIZATION,
    item=TextInput(title=Localizable("Protection Domain")),
    value_spec=_parameter_valuespec_prism_protection_domains,
)
