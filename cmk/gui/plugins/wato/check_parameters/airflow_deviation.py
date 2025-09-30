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
    Percentage,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_spec_airflow_deviation() -> Dictionary:
    return Dictionary(
        title=Title("Airflow Deviation measured at airflow sensors"),
        elements={
            "levels_upper": DictElement(
                required=False,
                parameter_form=TupleLevels(
                    title=Title("Upper levels"),
                    elements=[
                        Percentage(title=Title("warning at"), prefill=DefaultValue(20)),
                        Percentage(
                            title=Title("critical at"),
                            prefill=DefaultValue(20),
                        ),
                    ],
                ),
            ),
            "levels_lower": DictElement(
                required=False,
                parameter_form=TupleLevels(
                    title=Title("Lower levels"),
                    elements=[
                        Percentage(
                            title=Title("critical if below or equal"),
                            prefill=DefaultValue(-20),
                        ),
                        Percentage(
                            title=Title("warning if below or equal"),
                            prefill=DefaultValue(-20),
                        ),
                    ],
                ),
            ),
        },
    )


rule_spec_airflow_deviation = CheckParameters(
    name="airflow_deviation",
    title=Title("Airflow Deviation in Percent"),
    topic=Topic.ENVIRONMENTAL,
    parameter_form=_parameter_form_spec_airflow_deviation,
    condition=HostAndItemCondition(item_title=Title("Detector ID")),
)
