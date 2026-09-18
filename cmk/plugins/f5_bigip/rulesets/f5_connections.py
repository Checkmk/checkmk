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
    migrate_to_lower_integer_levels,
    migrate_to_upper_integer_levels,
    PredictiveLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_f5_connections() -> Dictionary:
    return Dictionary(
        elements={
            "conns": DictElement(
                parameter_form=Levels[int](
                    title=Title("Maximum number of connections"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="connections"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((25000, 30000)),
                    predictive=PredictiveLevels(
                        reference_metric="connections",
                        prefill_abs_diff=DefaultValue((5000, 10000)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                )
            ),
            "ssl_conns": DictElement(
                parameter_form=Levels[int](
                    title=Title("Maximum number of SSL connections"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="connections"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((25000, 30000)),
                    predictive=PredictiveLevels(
                        reference_metric="connections_ssl",
                        prefill_abs_diff=DefaultValue((5000, 10000)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                )
            ),
            "connections_rate": DictElement(
                parameter_form=Levels[int](
                    title=Title("Maximum connections per second"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="connections/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((500, 1000)),
                    predictive=PredictiveLevels(
                        reference_metric="connections_rate",
                        prefill_abs_diff=DefaultValue((100, 200)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                )
            ),
            "connections_rate_lower": DictElement(
                parameter_form=Levels[int](
                    title=Title("Minimum connections per second"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="connections/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((100, 50)),
                    predictive=PredictiveLevels(
                        reference_metric="connections_rate",
                        prefill_abs_diff=DefaultValue((100, 200)),
                    ),
                    migrate=migrate_to_lower_integer_levels,
                )
            ),
            "http_req_rate": DictElement(
                parameter_form=Levels[int](
                    title=Title("Maximum HTTP requests per second"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="requests/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((500, 1000)),
                    predictive=PredictiveLevels(
                        reference_metric="requests_per_second",
                        prefill_abs_diff=DefaultValue((100, 200)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                )
            ),
        },
    )


rule_spec_f5_connections = CheckParameters(
    name="f5_connections",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_f5_connections,
    title=Title("F5 load balancer connections"),
    condition=HostCondition(),
)
