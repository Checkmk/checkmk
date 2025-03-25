#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Float,
    InputHint,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

rule_spec_check_parameters = CheckParameters(
    title=Title("Splunk License Usage"),
    topic=Topic.APPLICATIONS,
    parameter_form=lambda: Dictionary(
        elements={
            # TODO: consider renaming if it is really a percentage of the quota.
            "usage_bytes": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Upper percentage levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=InputHint(value=(80.0, 90.0)),
                )
            ),
        },
    ),
    name="splunk_license_usage",
    condition=HostCondition(),
)
