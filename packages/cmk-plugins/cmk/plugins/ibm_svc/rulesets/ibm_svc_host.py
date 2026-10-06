#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    migrate_to_integer_simple_levels,
    SimpleLevels,
    SimpleLevelsConfigModel,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _upper_levels(title: Title, unit: str) -> DictElement[SimpleLevelsConfigModel[int]]:
    return DictElement(
        parameter_form=SimpleLevels[int](
            title=title,
            level_direction=LevelDirection.UPPER,
            form_spec_template=Integer(unit_symbol=unit),
            prefill_fixed_levels=InputHint((0, 0)),
            migrate=migrate_to_integer_simple_levels,
        ),
    )


def _parameter_form_ibm_svc_host() -> Dictionary:
    return Dictionary(
        elements={
            "active_hosts": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Count of active hosts"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="active hosts"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "inactive_hosts": _upper_levels(Title("Count of inactive hosts"), "inactive hosts"),
            "degraded_hosts": _upper_levels(Title("Count of degraded hosts"), "degraded hosts"),
            "offline_hosts": _upper_levels(Title("Count of offline hosts"), "offline hosts"),
            "other_hosts": _upper_levels(Title("Count of other hosts"), "other hosts"),
        },
    )


rule_spec_ibm_svc_host = CheckParameters(
    name="ibm_svc_host",
    title=Title("IBM SVC hosts"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_form_ibm_svc_host,
    condition=HostCondition(),
)
