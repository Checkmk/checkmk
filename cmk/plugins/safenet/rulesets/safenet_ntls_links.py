#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    Levels,
    LevelsType,
    migrate_to_upper_integer_levels,
    PredictiveLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_ruleset_safenet_ntls_links():
    return Dictionary(
        elements={
            "levels": DictElement(
                parameter_form=Levels(
                    title=Title("NTLS Links"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((1000, 2000)),
                    predictive=PredictiveLevels(
                        reference_metric="connections",
                        prefill_abs_diff=DefaultValue((1000, 2000)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                )
            )
        },
    )


rule_spec_safenet_ntls_clients = CheckParameters(
    name="safenet_ntls_links",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_ruleset_safenet_ntls_links,
    title=Title("Safenet NTLS Links"),
    condition=HostCondition(),
)
