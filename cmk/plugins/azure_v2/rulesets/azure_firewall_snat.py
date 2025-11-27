#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    Percentage,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset allows you to configure levels for Azure Firewall SNAT port utilization monitoring"
        ),
        elements={
            "snat_utilization": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("SNAT port utilization levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(title=Title("SNAT port utilization %")),
                    prefill_fixed_levels=InputHint((85.0, 95.0)),
                ),
            ),
        },
    )


rule_spec_azure_firewall_snat = CheckParameters(
    name="azure_v2_firewall_snat",
    title=Title("Azure Firewall SNAT Utilization"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
