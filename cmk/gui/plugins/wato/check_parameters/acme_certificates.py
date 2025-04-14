#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    LevelsType,
    migrate_to_float_simple_levels,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_rulespec_acme_certificates() -> Dictionary:
    return Dictionary(
        elements={
            "expire_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Time before the expiration date of the certificate"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ],
                    ),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((604800.0, 2592000.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
                required=True,
            )
        }
    )


rule_spec_acme_sbc_snmp = CheckParameters(
    parameter_form=_parameter_rulespec_acme_certificates,
    name="acme_certificates",
    title=Title("ACME Certificates"),
    topic=Topic.APPLICATIONS,
    condition=HostAndItemCondition(item_title=Title("Name of certificate")),
)
