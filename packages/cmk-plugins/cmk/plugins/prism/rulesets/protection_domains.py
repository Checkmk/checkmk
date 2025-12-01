#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_prism_protection_domains() -> Dictionary:
    return Dictionary(
        elements={
            "sync_state": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Target sync state"),
                    help_text=Help(
                        "Configure the target state of the protection domain sync state."
                    ),
                    elements=[
                        SingleChoiceElement(name="Enabled", title=Title("Sync enabled")),
                        SingleChoiceElement(name="Disabled", title=Title("Sync disabled")),
                        SingleChoiceElement(name="Synchronizing", title=Title("Syncing")),
                    ],
                    prefill=DefaultValue("Disabled"),
                )
            )
        },
    )


rule_spec_prims_protection_domains = CheckParameters(
    name="prism_protection_domains",
    title=Title("Nutanix Prism MetroAvail Sync State"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_prism_protection_domains,
    condition=HostAndItemCondition(item_title=Title("Protection Domain")),
)
