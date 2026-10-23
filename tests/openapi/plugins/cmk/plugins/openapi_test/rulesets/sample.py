#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    LevelsType,
    Password,
    SimpleLevels,
    String,
)
from cmk.rulesets.v1.rule_specs import (
    ActiveCheck,
    CheckParameters,
    HostCondition,
    SpecialAgent,
    Topic,
)

LEVELS_RULESET = "checkgroup_parameters:openapi_test_levels"
ACTIVE_CHECK_RULESET = "active_checks:openapi_test_check"
SPECIAL_AGENT_RULESET = "special_agents:openapi_test_agent"

LEVELS_VALUE_RAW = "{'levels': ('fixed', (10.0, 5.0))}"
ACTIVE_CHECK_VALUE_RAW = (
    '{"name": "check_localhost", "host": {"address": ("direct", "localhost")}, "mode": ("url", {})}'
)


def _levels_form() -> Dictionary:
    return Dictionary(
        elements={
            "levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Float(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((10.0, 5.0)),
                ),
            ),
        }
    )


rule_spec_levels = CheckParameters(
    name="openapi_test_levels",
    title=Title("REST API test levels"),
    topic=Topic.GENERAL,
    parameter_form=_levels_form,
    condition=HostCondition(),
)


def _active_check_form() -> Dictionary:
    return Dictionary(
        elements={
            "name": DictElement(required=True, parameter_form=String()),
            "host": DictElement(
                required=True,
                parameter_form=Dictionary(
                    elements={
                        "address": DictElement(
                            required=True,
                            parameter_form=CascadingSingleChoice(
                                elements=[
                                    CascadingSingleChoiceElement(
                                        name="direct",
                                        title=Title("Direct"),
                                        parameter_form=String(),
                                    ),
                                ],
                            ),
                        ),
                        "virthost": DictElement(parameter_form=String()),
                    }
                ),
            ),
            "mode": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    elements=[
                        CascadingSingleChoiceElement(
                            name="url",
                            title=Title("URL"),
                            parameter_form=Dictionary(
                                elements={
                                    "uri": DictElement(parameter_form=String()),
                                    "ssl": DictElement(parameter_form=String()),
                                    "expect_string": DictElement(parameter_form=String()),
                                    "urlize": DictElement(parameter_form=BooleanChoice()),
                                }
                            ),
                        ),
                    ],
                ),
            ),
        }
    )


rule_spec_active_check = ActiveCheck(
    name="openapi_test_check",
    title=Title("REST API test check"),
    topic=Topic.GENERAL,
    parameter_form=_active_check_form,
)


def _special_agent_form() -> Dictionary:
    return Dictionary(
        elements={
            "username": DictElement(required=True, parameter_form=String()),
            "password": DictElement(required=True, parameter_form=Password()),
        }
    )


rule_spec_special_agent = SpecialAgent(
    name="openapi_test_agent",
    title=Title("REST API test agent"),
    topic=Topic.GENERAL,
    parameter_form=_special_agent_form,
)
