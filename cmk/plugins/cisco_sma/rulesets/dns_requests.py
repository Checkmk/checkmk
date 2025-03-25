#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    LevelsType,
    SimpleLevels,
    SimpleLevelsConfigModel,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _dns_requests_form() -> Dictionary:
    return Dictionary(
        elements={
            "pending_dns_levels": DictElement[SimpleLevelsConfigModel[int]](
                parameter_form=SimpleLevels(
                    title=Title("Thresholds on pending DNS requests"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
            "outstanding_dns_levels": DictElement[SimpleLevelsConfigModel[int]](
                parameter_form=SimpleLevels(
                    title=Title("Thresholds on outstanding DNS requests"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
        }
    )


rule_spec_dns_requests = CheckParameters(
    name="cisco_sma_dns_requests",
    title=Title("Cisco SMA DNS requests"),
    topic=Topic.APPLICATIONS,
    parameter_form=_dns_requests_form,
    condition=HostCondition(),
)
