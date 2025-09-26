#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.generators.tuple_utils import TupleLevels
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, Float
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_spec_adva_ifs():
    return Dictionary(
        elements={
            "limits_output_power": DictElement(
                required=False,
                parameter_form=TupleLevels(
                    title=Title("Sending Power"),
                    elements=[
                        Float(title=Title("lower limit"), unit_symbol="dBm"),
                        Float(title=Title("upper limit"), unit_symbol="dBm"),
                    ],
                ),
            ),
            "limits_input_power": DictElement(
                required=False,
                parameter_form=TupleLevels(
                    title=Title("Received Power"),
                    elements=[
                        Float(title=Title("lower limit"), unit_symbol="dBm"),
                        Float(title=Title("upper limit"), unit_symbol="dBm"),
                    ],
                ),
            ),
        }
    )


rule_spec_adva_ifs = CheckParameters(
    name="adva_ifs",
    title=Title("Adva Optical Transport Laser Power"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_spec_adva_ifs,
    condition=HostAndItemCondition(item_title=Title("Interface")),
)
