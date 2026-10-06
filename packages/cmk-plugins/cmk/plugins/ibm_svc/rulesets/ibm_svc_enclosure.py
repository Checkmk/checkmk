#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    InputHint,
    Integer,
    LevelDirection,
    migrate_to_integer_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _migrate(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    result = dict(value)
    canisters = result.get("levels_lower_online_canisters")
    # Legacy "All must be online" was stored as ``False``.
    if canisters is False:
        result["levels_lower_online_canisters"] = ("all_online", None)
    # Legacy fixed levels were stored as a plain ``(warn, crit)`` tuple.
    elif isinstance(canisters, tuple) and len(canisters) == 2 and isinstance(canisters[0], int):
        result["levels_lower_online_canisters"] = (
            "levels",
            migrate_to_integer_simple_levels(canisters),
        )
    return result


def _parameter_form_ibm_svc_enclosure() -> Dictionary:
    return Dictionary(
        migrate=_migrate,
        elements={
            "levels_lower_online_canisters": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Lower levels for online canisters"),
                    help_text=Help(
                        "Without levels all canisters are expected to be online. "
                        "With fixed levels the warning and critical thresholds are "
                        "applied to the number of online canisters."
                    ),
                    prefill=DefaultValue("all_online"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="all_online",
                            title=Title("All must be online"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="levels",
                            title=Title("Specify levels"),
                            parameter_form=SimpleLevels[int](
                                level_direction=LevelDirection.LOWER,
                                form_spec_template=Integer(unit_symbol="online canisters"),
                                prefill_fixed_levels=InputHint((0, 0)),
                                migrate=migrate_to_integer_simple_levels,
                            ),
                        ),
                    ],
                ),
            ),
        },
    )


rule_spec_ibm_svc_enclosure = CheckParameters(
    name="ibm_svc_enclosure",
    title=Title("IBM SVC enclosure"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_form_ibm_svc_enclosure,
    condition=HostAndItemCondition(item_title=Title("Name of enclosure")),
)
