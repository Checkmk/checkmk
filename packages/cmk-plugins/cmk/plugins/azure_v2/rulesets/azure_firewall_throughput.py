#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    SIMagnitude,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset allows you to configure levels for Azure Firewall throughput monitoring"
        ),
        elements={
            "throughput": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Throughput levels (/sec)"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(
                        displayed_magnitudes=[
                            SIMagnitude.BYTE,
                            SIMagnitude.KILO,
                            SIMagnitude.MEGA,
                        ],
                    ),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
        },
    )


rule_spec_azure_firewall_throughput = CheckParameters(
    name="azure_v2_firewall_throughput",
    title=Title("Azure Firewall Throughput"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
