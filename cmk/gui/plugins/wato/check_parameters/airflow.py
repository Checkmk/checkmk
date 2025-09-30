#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.generators.tuple_utils import TupleLevels
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_spec_airflow() -> Dictionary:
    return Dictionary(
        elements={
            "level_low": DictElement(
                required=False,
                parameter_form=TupleLevels(
                    title=Title("Lower levels"),
                    elements=[
                        Float(
                            title=Title("Warning if below l/s"),
                            prefill=DefaultValue(5.0),
                        ),
                        Float(
                            title=Title("Critical if below l/s"),
                            prefill=DefaultValue(2.0),
                        ),
                    ],
                ),
            ),
            "level_high": DictElement(
                required=False,
                parameter_form=TupleLevels(
                    title=Title("Upper levels"),
                    elements=[
                        Float(
                            title=Title("Warning at l/s"),
                            prefill=DefaultValue(10.0),
                        ),
                        Float(
                            title=Title("Critical at l/s"),
                            prefill=DefaultValue(11.0),
                        ),
                    ],
                ),
            ),
        }
    )


rule_spec_airflow = CheckParameters(
    name="airflow",
    title=Title("Airflow levels"),
    topic=Topic.ENVIRONMENTAL,
    parameter_form=_parameter_form_spec_airflow,
    condition=HostCondition(),
)
