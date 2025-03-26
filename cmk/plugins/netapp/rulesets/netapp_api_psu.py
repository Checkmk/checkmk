#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import DiscoveryParameters, Topic


def _valuespec_discovery_netapp_api_psu_rules() -> Dictionary:
    return Dictionary(
        elements={
            "mode": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Specify discovery mode"),
                    help_text=Help(
                        "Option which allows to specify whether all power supply units will be grouped into one service (summary) or each unit gets allocated one individual service (single)."
                    ),
                    elements=[
                        SingleChoiceElement(name="summarize", title=Title("Summary")),
                        SingleChoiceElement(name="single", title=Title("Single")),
                    ],
                ),
            )
        },
    )


rule_spec_discovery_netapp_api_psu_rules = DiscoveryParameters(
    name="discovery_netapp_api_psu_rules",
    title=Title("Netapp power supply unit discovery"),
    topic=Topic.STORAGE,
    parameter_form=_valuespec_discovery_netapp_api_psu_rules,
)
