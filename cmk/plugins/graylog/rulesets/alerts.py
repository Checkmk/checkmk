#!/usr/bin/env python3

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_graylog_alerts():
    return Dictionary(
        title=Title("Graylog alerts"),
        elements={
            "alerts_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Total alerts count upper levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                )
            ),
            "alerts_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Total alerts count lower levels"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                )
            ),
            "events_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Total events count upper levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                )
            ),
            "events_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Total events count lower levels"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                )
            ),
        },
    )


rule_spec_graylog_alerts = CheckParameters(
    name="graylog_alerts",
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_parameter_form_graylog_alerts,
    title=Title("Graylog alerts"),
)
