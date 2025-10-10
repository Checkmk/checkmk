#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disable-error-code="no-untyped-def"
from cmk.gui.form_specs.unstable.legacy_converter.generators import OptionalTupleLevels
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, HostCondition, Topic


def _parameter_form_spec_connections():
    return Dictionary(
        title=Title("Levels connections"),
        elements={
            "active_connections_lower": DictElement(
                required=False,
                parameter_form=OptionalTupleLevels(
                    title=Title("Lower levels for active connections"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
            "active_connections": DictElement(
                required=False,
                parameter_form=OptionalTupleLevels(
                    title=Title("Upper levels for active connections"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
            "failed_connections": DictElement(
                required=False,
                parameter_form=OptionalTupleLevels(
                    title=Title("Failed connections"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
        },
    )


rule_spec_database_connections = CheckParameters(
    name="database_connections",
    title=Title("Azure database connections (deprecated)"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_connections,
    condition=HostAndItemCondition(item_title=Title("Database")),
)

rule_spec_azure_v2_database_connections = CheckParameters(
    name="azure_v2_database_connections",
    title=Title("Azure database connections"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_connections,
    condition=HostCondition(),
)
