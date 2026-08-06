#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, Integer
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "interval": DictElement(
                parameter_form=Integer(
                    title=Title("Timespan for mail rate computation"),
                    help_text=Help(
                        "If set, the mail rates are averaged over this timespan. "
                        "Without it, the rate of the last check interval is reported."
                    ),
                    unit_symbol="minutes",
                    prefill=DefaultValue(60),
                ),
            ),
        },
    )


rule_spec_fireeye_mail = CheckParameters(
    name="fireeye_mail",
    title=Title("FireEye mail rate average"),
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_parameter_form,
)
