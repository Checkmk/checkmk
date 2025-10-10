#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disable-error-code="no-untyped-def"
from cmk.gui.form_specs.unstable.legacy_converter.generators import TupleLevels
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Percentage,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_spec_battery() -> Dictionary:
    return Dictionary(
        help_text=Help("This Ruleset sets the threshold limits for battery sensors"),
        elements={
            "levels": DictElement(
                required=False,
                parameter_form=TupleLevels(
                    title=Title("Upper levels"),
                    elements=[
                        Percentage(title=Title("Warning at")),
                        Percentage(title=Title("Critical at")),
                    ],
                ),
            ),
            "levels_lower": DictElement(
                required=False,
                parameter_form=TupleLevels(
                    title=Title("Lower levels"),
                    elements=[
                        Percentage(title=Title("Warning below")),
                        Percentage(title=Title("Critical below")),
                    ],
                ),
            ),
        },
        ignored_elements=("_item_key",),
    )


rule_spec_battery = CheckParameters(
    name="battery",
    title=Title("Battery Levels"),
    topic=Topic.ENVIRONMENTAL,
    parameter_form=_parameter_form_spec_battery,
    condition=HostAndItemCondition(item_title=Title("Sensor name")),
)
